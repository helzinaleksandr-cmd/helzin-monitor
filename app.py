import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация памяти
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

# --- САЙДБАР (АДМИНКА) ---
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=None, placeholder="Цена...")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...")
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...")
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - (sl if sl else entry))
                reward = abs((tp if tp else entry) - entry)
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": new_coin, "side": side, "entry": float(entry),
                    "qty": float(qty), "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, "rr": round(reward/risk, 2) if risk > 0 else 0.0, 
                    "status": "В процессе ⏳", "final_pnl": None 
                })
                st.rerun()

# --- ОСНОВНОЙ ДВИЖОК (ПЛАВНОЕ ОБНОВЛЕНИЕ 5 СЕК) ---
@st.fragment(run_every=5)
def terminal_engine():
    # 1. Получение данных
    df, cur_p = get_crypto_data(st.session_state.ticker, st.session_state.tf)
    if cur_p > 0: st.session_state.price = cur_p

    # 2. Логика проверки сделок
    total_pnl = 0.0
    pnl_history = [st.session_state.balance] # Для кривой доходности
    
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            p_check = cur_p if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
            if p_check > 0:
                is_closed = False
                pnl = (p_check - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_check) * trade["qty"]
                if trade["side"] == "LONG":
                    if p_check >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                    elif p_check <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
                else:
                    if p_check <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                    elif p_check >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
                if is_closed: trade["final_pnl"] = pnl
        
        if trade["final_pnl"] is not None:
            total_pnl += trade["final_pnl"]
            pnl_history.append(st.session_state.balance + total_pnl)

    # 3. ВКЛАДКИ
    tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал сделок"])

    with tab_trade:
        # Верхняя панель управления
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1: 
            t_in = st.text_input("Тикер", value=st.session_state.ticker).upper()
            if t_in != st.session_state.ticker: st.session_state.ticker = t_in; st.rerun()
        with c2: st.selectbox("Биржа", ["Binance (Spot)"])
        with c3:
            st.write("Таймфрейм")
            t_cols = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if t_cols[i].button(t, key=f"t_{t}", type="primary" if st.session_state.tf == t else "secondary", use_container_width=True):
                    st.session_state.tf = t; st.rerun()

        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {st.session_state.ticker}", f"${st.session_state.price:,.2f}")
        m2.metric("Баланс + Профит", f"${(st.session_state.balance + total_pnl):,.2f}", f"{total_pnl:+.2f}$")
        m3.metric("Активных позиций", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        # ГРАФИК ЦЕНЫ
        if df is not None:
            fig_chart = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig_chart.update_layout(
                template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=50, t=10, b=10),
                yaxis=dict(side="right", tickformat="$.2f")
            )
            fig_chart.add_hline(y=st.session_state.price, line_dash="dash", line_color="yellow")
            st.plotly_chart(fig_chart, use_container_width=True)

        # КРИВАЯ ДОХОДНОСТИ (сразу под графиком)
        st.subheader("📈 Кривая доходности (Equity)")
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(y=pnl_history, mode='lines+markers', line=dict(color='#00FFCC', width=3), fill='tozeroy'))
        fig_pnl.update_layout(
            template="plotly_dark", height=250, 
            margin=dict(l=0, r=50, t=10, b=10),
            yaxis=dict(side="right"),
            xaxis=dict(title="Кол-во сделок")
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    with tab_journal:
        st.subheader("📓 Полный журнал сделок")
        if st.session_state.trades:
            # Таблица
            h = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
            names = ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "PnL ($)", "Статус", ""]
            for col, n in zip(h, names): col.markdown(f"**{n}**")
            
            for i, trade in enumerate(st.session_state.trades):
                p_disp = trade["final_pnl"] if trade["final_pnl"] is not None else (
                    (st.session_state.price - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" and trade["coin"] == st.session_state.ticker else 0.0
                )
                cols = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
                cols[0].write(trade["time"]); cols[1].write(trade["coin"]); cols[2].write(trade["side"])
                cols[3].write(f"{trade['qty']}"); cols[4].write(f"{trade['entry']:.2f}")
                cols[5].write(f"{trade['sl']:.2f}"); cols[6].write(f"{trade['tp']:.2f}")
                cols[7].write(f"{trade['rr']}")
                p_color = "🟢" if (isinstance(p_disp, float) and p_disp >= 0) else "🔴"
                cols[8].write(f"{p_color} ${p_disp:.2f}")
                cols[9].write(trade["status"])
                if cols[10].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades.pop(i); st.rerun()
        else:
            st.info("Здесь будет список ваших сделок после открытия первой позиции.")

# Запуск
terminal_engine()
