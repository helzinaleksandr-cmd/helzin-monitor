import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"
if 'ticker' not in st.session_state: st.session_state.ticker = "BTC"

def get_crypto_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df, float(df['close'].iloc[-1])
    except: return None, 0.0
    return None, 0.0

# --- САЙДБАР ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Депозит ($)", value=float(st.session_state.balance))
    st.divider()
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=None)
        qty = st.number_input("Кол-во", value=None, step=0.0001)
        sl = st.number_input("Стоп", value=None)
        tp = st.number_input("Тейк", value=None)
        img_entry = st.file_uploader("🖼 Скриншот (ВХОД)", type=['png', 'jpg'])
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now(),
                    "coin": new_coin, "side": side, "entry": float(entry),
                    "qty": float(qty), "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, "status": "В процессе ⏳", 
                    "final_pnl": None, "img_entry": img_entry, "img_exit": None
                })
                st.rerun()

# --- ДВИЖОК ОБНОВЛЕНИЯ ---
@st.fragment(run_every=5)
def terminal_engine():
    df, cur_p = get_crypto_data(st.session_state.ticker, st.session_state.tf)
    if cur_p > 0: st.session_state.price = cur_p

    total_closed_pnl = 0.0
    closed_trades_data = [] # Список для графика доходности
    
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            p_check = cur_p if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
            if p_check > 0:
                is_closed = False
                res = (p_check - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_check) * trade["qty"]
                if trade["side"] == "LONG":
                    if trade["tp"] > 0 and p_check >= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check <= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                else:
                    if trade["tp"] > 0 and p_check <= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check >= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                if is_closed: 
                    trade["final_pnl"] = res
                    trade["close_time"] = datetime.now() # Записываем время закрытия
        
        if trade["final_pnl"] is not None:
            total_closed_pnl += trade["final_pnl"]
            closed_trades_data.append({
                "time": trade.get("close_time", trade["time"]),
                "pnl": trade["final_pnl"]
            })

    t_trade, t_journal = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ И РАЗБОР"])

    with t_trade:
        # Панель параметров
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1: 
            t_in = st.text_input("Тикер", value=st.session_state.ticker).upper(); st.session_state.ticker = t_in
        with c2: st.selectbox("Биржа", ["Binance"])
        with c3:
            st.write("Таймфрейм")
            cols = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if cols[i].button(t, key=f"tf_{t}", type="primary" if st.session_state.tf == t else "secondary"):
                    st.session_state.tf = t; st.rerun()

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {st.session_state.ticker}", f"${st.session_state.price:,.2f}")
        m2.metric("Баланс + Профит", f"${(st.session_state.balance + total_closed_pnl):,.2f}", f"{total_closed_pnl:+.2f}$")
        m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=50, t=10, b=10), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)

        # --- БЛОК КРИВОЙ ДОХОДНОСТИ С ФИЛЬТРАМИ ---
        st.divider()
        st.subheader("📊 Аналитика доходности")
        
        p_col1, p_col2 = st.columns([2, 1])
        with p_col1:
            period = st.radio("Период", ["День", "7 Дней", "Месяц", "Год", "Все время"], horizontal=True)
        with p_col2:
            chart_type = st.selectbox("Вид графика", ["Линия (Equity)", "Столбцы (PnL per trade)"])

        # Фильтрация данных
        now = datetime.now()
        if period == "День": start_date = now - timedelta(days=1)
        elif period == "7 Дней": start_date = now - timedelta(days=7)
        elif period == "Месяц": start_date = now - timedelta(days=30)
        elif period == "Год": start_date = now - timedelta(days=365)
        else: start_date = datetime(2000, 1, 1)

        filtered_data = [d for d in closed_trades_data if d["time"] >= start_date]
        
        if filtered_data:
            y_values = []
            current_equity = st.session_state.balance
            # Для линии считаем накопление, для столбцов - чистый pnl
            if chart_type == "Линия (Equity)":
                y_values = [current_equity]
                for d in filtered_data:
                    current_equity += d["pnl"]
                    y_values.append(current_equity)
                fig_p = go.Figure(go.Scatter(y=y_values, mode='lines+markers', line=dict(color='#00FFCC', width=3), fill='tozeroy'))
            else:
                pnls = [d["pnl"] for d in filtered_data]
                colors = ['#00FFCC' if p >= 0 else '#FF4B4B' for p in pnls]
                fig_p = go.Figure(go.Bar(y=pnls, marker_color=colors))

            fig_p.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=50, t=10, b=10), yaxis=dict(side="right"))
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("Нет закрытых сделок за выбранный период")

    with t_journal:
        # (Тут остается твой журнал с Expanders и скриншотами)
        st.subheader("📓 История сделок")
        for i, trade in enumerate(st.session_state.trades):
            with st.expander(f"{trade['time'].strftime('%H:%M:%S')} | {trade['coin']} | PnL: {trade['final_pnl'] if trade['final_pnl'] else '...'} | {trade['status']}"):
                # Внутрянка экспандера как в прошлом коде...
                st.write(f"Вход: {trade['entry']} | Скрин входа есть" if trade['img_entry'] else "Скрин входа нет")
                if st.button("Удалить", key=f"del_{trade['id']}"):
                    st.session_state.trades.pop(i); st.rerun()

terminal_engine()
