import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'ticker' not in st.session_state: st.session_state.ticker = "BTC"
if 'market_type' not in st.session_state: st.session_state.market_type = "SPOT"
if 'tf' not in st.session_state: st.session_state.tf = "15m"

def get_binance_data(symbol, market_type, tf):
    # Переключение между Спотом и Фьючерсами
    base_url = "https://fapi.binance.com/fapi/v1/klines" if market_type == "FUTURES" else "https://api.binance.com/api/v3/klines"
    pair = f"{symbol}USDT"
    params = {"symbol": pair, "interval": tf, "limit": 100}
    try:
        res = requests.get(base_url, params=params, timeout=3)
        data = res.json()
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close']: df[col] = df[col].astype(float)
        return df, df['close'].iloc[-1]
    except: return None, 0.0

# --- 2. САЙДБАР ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Нач. Депозит ($)", value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Монета (без USDT)", "BTC").upper()
        entry = st.number_input("Цена входа", value=None)
        qty = st.number_input("Кол-во монет", value=None, step=0.0001)
        sl = st.number_input("Стоп-лосс", value=None)
        tp = st.number_input("Тейк-профит", value=None)
        img_entry = st.file_uploader("🖼 Скриншот (ВХОД)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now(),
                    "coin": new_coin, "market": st.session_state.market_type, "side": side, 
                    "entry": float(entry), "qty": float(qty), "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, "status": "В процессе ⏳", 
                    "final_pnl": None, "img_entry": img_entry, "img_exit": None
                })
                st.rerun()
    
    st.divider()
    # ЭКСПОРТ
    if st.session_state.trades:
        df_export = pd.DataFrame(st.session_state.trades).drop(columns=['img_entry', 'img_exit', 'id'], errors='ignore')
        st.download_button("📥 СКАЧАТЬ В EXCEL (CSV)", data=df_export.to_csv(index=False).encode('utf-8-sig'), 
                           file_name="trades.csv", mime="text/csv", use_container_width=True)

# --- 3. ОСНОВНОЙ ДВИЖОК ---
@st.fragment(run_every=5)
def terminal_engine():
    df, cur_p = get_binance_data(st.session_state.ticker, st.session_state.market_type, st.session_state.tf)
    
    # Расчет PnL
    total_pnl = 0.0
    for t in st.session_state.trades:
        if "⏳" in t["status"]:
            # Проверка цены (если монета та же, берем cur_p, иначе запрашиваем)
            p_check = cur_p if t["coin"] == st.session_state.ticker else get_binance_data(t["coin"], t["market"], "5m")[1]
            if p_check > 0:
                res = (p_check - t["entry"]) * t["qty"] if t["side"] == "LONG" else (t["entry"] - p_check) * t["qty"]
                # Авто-закрытие по SL/TP
                if t["side"] == "LONG":
                    if t["tp"] > 0 and p_check >= t["tp"]: t["status"] = "Тейк ✅"; t["final_pnl"] = res
                    elif t["sl"] > 0 and p_check <= t["sl"]: t["status"] = "Стоп ❌"; t["final_pnl"] = res
                else:
                    if t["tp"] > 0 and p_check <= t["tp"]: t["status"] = "Тейк ✅"; t["final_pnl"] = res
                    elif t["sl"] > 0 and p_check >= t["sl"]: t["status"] = "Стоп ❌"; t["final_pnl"] = res
        if t["final_pnl"] is not None: total_pnl += t["final_pnl"]

    t_trade, t_journal, t_stats = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ", "📊 СТАТИСТИКА"])

    with t_trade:
        # Панель выбора
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: 
            st.session_state.ticker = st.text_input("Тикер", value=st.session_state.ticker).upper()
        with c2:
            m_choice = st.selectbox("Рынок", ["SPOT", "FUTURES"], index=0 if st.session_state.market_type == "SPOT" else 1)
            if m_choice != st.session_state.market_type:
                st.session_state.market_type = m_choice
                st.rerun()
        with c3:
            st.write("Таймфрейм")
            tc = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if tc[i].button(t, key=f"tf_{t}", type="primary" if st.session_state.tf == t else "secondary"):
                    st.session_state.tf = t; st.rerun()

        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {st.session_state.market_type}", f"${cur_p:,.2f}")
        m2.metric("Баланс + PnL", f"${(st.session_state.balance + total_pnl):,.2f}")
        m3.metric("Профит", f"${total_pnl:+.2f}")

        # График
        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=50, t=10, b=10), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)

    with t_journal:
        for i, trade in enumerate(st.session_state.trades):
            with st.expander(f"{trade['coin']} | {trade['side']} | {trade['status']} | PnL: ${trade.get('final_pnl', 0.0):.2f}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"Вход: {trade['entry']}")
                    if st.button("🗑 Удалить", key=f"del_{trade['id']}"):
                        st.session_state.trades.pop(i); st.rerun()
                with c2: 
                    st.write("Скрин Входа:")
                    if trade['img_entry']: st.image(trade['img_entry'])
                with c3:
                    st.write("Скрин Выхода:")
                    if trade['img_exit']: st.image(trade['img_exit'])
                    elif trade['final_pnl'] is not None:
                        up = st.file_uploader("Загрузить выход", key=f"ex_{trade['id']}")
                        if up: trade['img_exit'] = up; st.rerun()

    with t_stats:
        st.subheader("Результаты")
        st.write(f"Всего сделок: {len(st.session_state.trades)}")
        # Здесь можно добавить график кривой доходности, который мы обсуждали

terminal_engine()
