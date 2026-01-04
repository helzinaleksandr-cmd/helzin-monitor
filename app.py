import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация всех данных
if 'trades' not in st.session_state: st.session_state.trades = []
if 'history' not in st.session_state: st.session_state.history = []
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'balance' not in st.session_state: st.session_state.balance = 1000.0

# Функция загрузки данных
def get_market_data(symbol, tf, market_type):
    exchange = "BinanceFutures" if market_type == "FUTURES" else "Binance"
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=150&aggregate={ag[tf]}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            st.session_state.price = float(df['close'].iloc[-1])
            return df
    except: return None
    return None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.title("👤 admin")
    # ВОЗВРАЩАЕМ ДЕПОЗИТ
    st.session_state.balance = st.number_input("Депозит ($)", value=st.session_state.balance, step=100.0)
    st.divider()
    
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=float(st.session_state.price), format="%.2f")
        # ПУСТЫЕ ГРАФЫ (как ты просил)
        amt = st.number_input("Кол-во монет", value=0.0, step=0.01)
        sl = st.number_input("Стоп-лосс", value=0.0, format="%.2f")
        tp = st.number_input("Тейк-профит", value=0.0, format="%.2f")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if amt > 0 and sl > 0 and tp > 0:
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(),
                    "time": datetime.now().strftime("%H:%M"),
                    "coin": coin, "side": side, "entry": entry,
                    "amt": amt, "sl": sl, "tp": tp, "status": "OPEN"
                })
                st.rerun()
            else:
                st.error("Заполните все поля!")

# --- ВЕРХНЯЯ ПАНЕЛЬ ---
c1, c2, c3 = st.columns([1, 1, 2])
with c1: market_type = st.selectbox("Рынок", ["SPOT", "FUTURES"])
with c2: ticker = st.text_input("Тикер", "BTC").upper()
with c3:
    st.write("Таймфрейм")
    tfs = st.columns(5)
    selected_tf = st.session_state.get('tf', "15m")
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if tfs[i].button(f, key=f): 
            st.session_state.tf = f
            st.rerun()

df = get_market_data(ticker, st.session_state.get('tf', "15m"), market_type)

# Авто-проверка статуса сделок
cur_p = st.session_state.price
for t in st.session_state.trades[:]:
    closed = False
    if t['side'] == "LONG":
        if cur_p >= t['tp']: closed, res = True, "PROFIT ✅"
        elif cur_p <= t['sl']: closed, res = True, "STOP ❌"
    else: # SHORT
        if cur_p <= t['tp']: closed, res = True, "PROFIT ✅"
        elif cur_p >= t['sl']: closed, res = True, "STOP ❌"
    
    if closed:
        t['status'] = res
        st.session_state.history.append(t)
        st.session_state.trades.remove(t)

# МЕТРИКИ (Цена, Баланс, Сделки)
m1, m2, m3 = st.columns(3)
m1.metric(f"Цена {market_type}", f"${cur_p:,.2f}")
m2.metric("Баланс", f"${st.session_state.balance:,.2f}")
m3.metric("Активных сделок", len(st.session_state.trades))

# --- ГРАФИК ---
if df is not None:
    fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    for t in st.session_state.trades:
        if t['coin'] == ticker:
            fig.add_hline(y=t['entry'], line_color="white", annotation_text="Вход")
            fig.add_hline(y=t['tp'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
            fig.add_hline(y=t['sl'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- ТАБЛИЦЫ ---
st.divider()
t1, t2 = st.tabs(["🔥 В РАБОТЕ", "📜 ИСТОРИЯ"])
with t1:
    if st.session_state.trades:
        for t in st.session_state.trades:
            col = st.columns([1, 1, 1, 1, 1, 1, 0.5])
            col[0].write(t['time'])
            col[1].write(f"**{t['coin']} {t['side']}**")
            col[2].write(f"Вход: {t['entry']}")
            col[3].write(f"Кол-во: {t['amt']}")
            col[4].write(f"TP: {t['tp']}")
            col[5].write(f"SL: {t['sl']}")
            if col[6].button("✖", key=t['id']):
                st.session_state.trades.remove(t); st.rerun()
    else: st.info("Нет активных сделок")

with t2:
    if st.session_state.history:
        for h in reversed(st.session_state.history):
            st.write(f"{h['time']} | {h['coin']} | {h['side']} | Результат: **{h['status']}**")
