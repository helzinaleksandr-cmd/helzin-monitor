import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация
if 'trades' not in st.session_state: st.session_state.trades = []
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"

# Функция загрузки
def get_crypto_data(symbol, tf, market):
    ex = "BinanceFutures" if market == "FUTURES" else "Binance"
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={symbol}&tsym=USDT&limit=200&aggregate={ag[tf]}&e={ex}"
        if "h" in tf: url = url.replace("minute", "hour")
        if "d" in tf: url = url.replace("minute", "day")
        
        res = requests.get(url, timeout=5).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            st.session_state.price = float(df['close'].iloc[-1])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
    except: return None
    return None

# ИНТЕРФЕЙС
with st.sidebar:
    st.title("👤 admin")
    with st.form("trade"):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Вход", value=float(st.session_state.price), format="%.2f")
        amt = st.text_input("Кол-во")
        sl = st.text_input("Стоп")
        tp = st.text_input("Тейк")
        if st.form_submit_button("ОТКРЫТЬ", use_container_width=True):
            try:
                st.session_state.trades.append({"id": datetime.now().timestamp(), "coin": coin, "side": side, "entry": entry, "amt": float(amt), "sl": float(sl), "tp": float(tp)})
                st.rerun()
            except: st.error("Ошибка!")

# Верхняя панель
c1, c2, c3 = st.columns([1, 1, 2])
current_coin = c1.text_input("Тикер", "BTC").upper()
market_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
with c3:
    st.write("Таймфрейм")
    ts = st.columns(5)
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if ts[i].button(f, key=f, type="primary" if st.session_state.tf == f else "secondary"):
            st.session_state.tf = f; st.rerun()

# График
df = get_crypto_data(current_coin, st.session_state.tf, market_type)

m1, m2 = st.columns(2)
m1.metric(f"Цена {market_type}", f"${st.session_state.price:,.2f}")
m2.metric("Активных сделок", len(st.session_state.trades))

if df is not None:
    fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    for t in st.session_state.trades:
        if t['coin'] == current_coin:
            fig.add_hline(y=t['entry'], line_color="white")
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Ожидание данных...")

# Список сделок
for t in st.session_state.trades:
    st.write(f"{t['coin']} {t['side']} @ {t['entry']}")
