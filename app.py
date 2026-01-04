import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# 1. Инициализация (как в твоей самой стабильной версии)
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0

def get_data(symbol, tf, market):
    ex = "BinanceFutures" if market == "FUTURES" else "Binance"
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag[tf]}&e={ex}"
        res = requests.get(url, timeout=5).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            st.session_state.price = float(df['close'].iloc[-1])
            return df
    except: return None
    return None

# --- SIDEBAR (Твой классический admin с депозитом) ---
with st.sidebar:
    st.title("👤 admin")
    st.session_state.balance = st.number_input("Депозит ($)", value=st.session_state.balance)
    st.divider()
    
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # Поля пустые (0.0), как на твоем скриншоте 19:18
        entry = st.number_input("Цена входа", value=0.0, format="%.2f")
        qty = st.number_input("Кол-во монет", value=0.0)
        sl = st.number_input("Стоп", value=0.0, format="%.2f")
        tp = st.number_input("Тейк", value=0.0, format="%.2f")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            # РАСЧЕТ RR (автоматически)
            rr = 0.0
            if sl > 0 and tp > 0 and entry > 0:
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                if risk > 0: rr = round(reward / risk, 2)

            if qty > 0:
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin, "side": side, "entry": entry,
                    "qty": qty, "sl": sl, "tp": tp, "rr": rr, "status": "В процессе ⏳"
                })
                st.rerun()

# --- ОСНОВНОЙ ИНТЕРФЕЙС (Вкладки) ---
tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: ticker = st.text_input("Тикер", "BTC").upper()
    with c2: m_type = st.selectbox("Рынок", ["FUTURES", "SPOT"])
    with c3:
        st.write("Таймфрейм")
        tfs = st.columns(5)
        for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
            if tfs[i].button(f, key=f): st.session_state.tf = f; st.rerun()

    df = get_data(ticker, st.session_state.get('tf', "15m"), m_type)
    cur_p = st.session_state.price

    # Авто-обновление статусов сделок по цене
    for t in st.session_state.trades:
        if t['status'] == "В процессе ⏳":
            if t['side'] == "LONG":
                if cur_p >= t['tp'] and t['tp'] > 0: t['status'] = "Тейк-профит ✅"
                elif cur_p <= t['sl'] and t['sl'] > 0: t['status'] = "Стоп-лосс ❌"
            else: # SHORT
                if cur_p <= t['tp'] and t['tp'] > 0: t['status'] = "Тейк-профит ✅"
                elif cur_p >= t['sl'] and t['sl'] > 0: t['status'] = "Стоп-лосс ❌"

    # Метрики
    m1, m2, m3 = st.columns(3)
    m1.metric("Цена", f"${cur_p:,.2f}")
    m2.metric("Баланс", f"${st.session_state.balance:,.2f}")
    m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t['status']]))

    if df is not None:
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with tab_journal:
    st.subheader("Журнал сделок")
    if st.session_state.trades:
        # ЗАГОЛОВКИ (как ты просил)
        h = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 0.5])
        names = ["Время", "Монета", "Тип", "Вход", "Стоп", "Тейк", "RR", "Статус", ""]
        for col, name in zip(h, names): col.write(f"**{name}**")
        
        # СТРОКИ С ДАННЫМИ
        for i, t in enumerate(st.session_state.trades):
            r = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 0.5])
            r[0].write(t['time'])
            r[1].write(t['coin'])
            r[2].write(t['side'])
            r[3].write(t['entry'])
            r[4].write(t['sl'])
            r[5].write(t['tp'])
            r[6].write(f"**{t['rr']}**")
            r[7].write(t['status'])
            if r[8].button("🗑", key=f"del_{i}"):
                st.session_state.trades.pop(i)
                st.rerun()
    else:
        st.info("Сделок пока нет.")
