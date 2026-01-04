import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Auto-Terminal", layout="wide")

# Инициализация
if 'trades' not in st.session_state: st.session_state.trades = []
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"

def get_crypto_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    try:
        suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
        url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag[tf]}&e=BinanceFutures"
        res = requests.get(url, timeout=5).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            st.session_state.price = float(df['close'].iloc[-1])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
    except: return None
    return None

# --- ЛОГИКА АВТО-ПРОВЕРКИ СДЕЛКИ ---
def update_trade_statuses(current_price):
    for t in st.session_state.trades:
        if t['status'] == "В ПРОЦЕССЕ ⏳":
            if t['side'] == "LONG":
                if current_price >= t['tp']: t['status'] = "ТЕЙК ✅"
                elif current_price <= t['sl']: t['status'] = "СТОП ❌"
            else: # SHORT
                if current_price <= t['tp']: t['status'] = "ТЕЙК ✅"
                elif current_price >= t['sl']: t['status'] = "СТОП ❌"

# --- ИНТЕРФЕЙС ---
with st.sidebar:
    st.title("➕ НОВАЯ СДЕЛКА")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        ent = st.number_input("Вход", value=float(st.session_state.price), format="%.2f")
        amt = st.number_input("Кол-во монет", value=0.1)
        sl = st.number_input("Стоп", value=ent*0.99)
        tp = st.number_input("Тейк", value=ent*1.02)
        
        if st.form_submit_button("ВЫСТАВИТЬ"):
            st.session_state.trades.append({
                "time": datetime.now().strftime("%H:%M"),
                "coin": coin, "side": side, "entry": ent,
                "amt": amt, "sl": sl, "tp": tp, "status": "В ПРОЦЕССЕ ⏳"
            })
            st.rerun()

c1, c2 = st.columns([1, 3])
active_coin = c1.text_input("Валюта", "BTC").upper()
with c2:
    ts = st.columns(5)
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if ts[i].button(f, key=f): st.session_state.tf = f; st.rerun()

df = get_crypto_data(active_coin, st.session_state.tf)
update_trade_statuses(st.session_state.price) # Проверяем статус сделок по текущей цене

# Метрики
st.columns(3)[0].metric("Цена Futures", f"${st.session_state.price:,.2f}")

if df is not None:
    fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- ТАБЛИЦА С АВТО-СТАТУСОМ ---
st.subheader("📑 Журнал сделок (Авто-обновление)")
if st.session_state.trades:
    df_trades = pd.DataFrame(st.session_state.trades)
    # Красивое отображение таблицы
    st.table(df_trades[['time', 'coin', 'side', 'entry', 'sl', 'tp', 'status']])
    
    if st.button("Очистить историю"):
        st.session_state.trades = []
        st.rerun()
else:
    st.info("Сделок пока нет.")
