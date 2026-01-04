import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Настройки страницы
st.set_page_config(page_title="Helzin Terminal", layout="wide")

# Инициализация хранилища
if 'trades' not in st.session_state: st.session_state.trades = []
if 'history' not in st.session_state: st.session_state.history = []
if 'price' not in st.session_state: st.session_state.price = 0.0

# 1. Функция получения данных
def get_market_data(symbol, tf, market_type):
    exchange = "BinanceFutures" if market_type == "FUTURES" else "Binance"
    # Маппинг таймфреймов
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

# 2. Боковая панель (Твоя рабочая форма)
with st.sidebar:
    st.title("👨‍💻 Admin")
    st.subheader("Новая сделка")
    
    with st.form("trade_form"):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # Авто-подстановка текущей цены
        entry = st.number_input("Цена входа", value=float(st.session_state.price), format="%.2f")
        amt = st.number_input("Кол-во монет", value=1.0, step=0.1)
        sl = st.number_input("Стоп-лосс", value=entry*0.99, format="%.2f")
        tp = st.number_input("Тейк-профит", value=entry*1.02, format="%.2f")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            st.session_state.trades.append({
                "id": datetime.now().timestamp(),
                "time": datetime.now().strftime("%H:%M"),
                "coin": coin, "side": side, "entry": entry,
                "amt": amt, "sl": sl, "tp": tp, "status": "OPEN"
            })
            st.rerun()

# 3. Основной экран
col_info, col_tf = st.columns([1, 2])
with col_info:
    m_type = st.selectbox("Рынок", ["SPOT", "FUTURES"])
    ticker = st.text_input("Тикер", "BTC").upper()

with col_tf:
    st.write("Таймфрейм")
    tfs = st.columns(5)
    selected_tf = "15m"
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if tfs[i].button(f): selected_tf = f

# Загрузка графика и цен
df = get_market_data(ticker, selected_tf, m_type)

# ЛОГИКА АВТО-ЗАКРЫТИЯ (Проверка Тейка и Стопа)
current_p = st.session_state.price
for t in st.session_state.trades[:]:
    if t['status'] == "OPEN":
        closed = False
        res_text = ""
        if t['side'] == "LONG":
            if current_p >= t['tp']: closed, res_text = True, "PROFIT ✅"
            elif current_p <= t['sl']: closed, res_text = True, "STOP ❌"
        else: # SHORT
            if current_p <= t['tp']: closed, res_text = True, "PROFIT ✅"
            elif current_p >= t['sl']: closed, res_text = True, "STOP ❌"
        
        if closed:
            t['status'] = res_text
            st.session_state.history.append(t)
            st.session_state.trades.remove(t)

# Отрисовка
st.metric(f"Цена {m_type}", f"${current_p:,.2f}")

if df is not None:
    fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    # Рисуем линии только для активной монеты
    for t in st.session_state.trades:
        if t['coin'] == ticker:
            fig.add_hline(y=t['entry'], line_color="white")
            fig.add_hline(y=t['tp'], line_dash="dash", line_color="#00ff88")
            fig.add_hline(y=t['sl'], line_dash="dash", line_color="#ff4b4b")
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# 4. ЖУРНАЛ СДЕЛОК (Как ты просил)
st.divider()
tab1, tab2 = st.tabs(["🔥 АКТИВНЫЕ", "📜 ИСТОРИЯ"])

with tab1:
    if st.session_state.trades:
        for t in st.session_state.trades:
            c = st.columns([1,1,1,1,1,1,0.5])
            c[0].write(t['time'])
            c[1].write(f"**{t['coin']} {t['side']}**")
            c[2].write(f"Вход: {t['entry']}")
            c[3].write(f"Кол-во: {t['amt']}")
            c[4].write(f"TP: {t['tp']}")
            c[5].write(f"SL: {t['sl']}")
            if c[6].button("✖", key=t['id']):
                st.session_state.trades.remove(t); st.rerun()
    else: st.info("Нет открытых позиций")

with tab2:
    if st.session_state.history:
        for h in reversed(st.session_state.history):
            st.write(f"{h['time']} | {h['coin']} | {h['side']} | Результат: **{h['status']}**")
    if st.button("Очистить историю"):
        st.session_state.history = []; st.rerun()
