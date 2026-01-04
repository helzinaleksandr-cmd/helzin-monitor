import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Terminal", layout="wide")

# Инициализация состояний (то, что было в самом начале)
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'history' not in st.session_state: st.session_state.history = []

# Функция получения данных (Чистый SPOT/FUTURES)
def get_data(symbol, tf, market):
    ex = "BinanceFutures" if market == "FUTURES" else "Binance"
    # Базовые интервалы для Cryptocompare
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    limit = 100
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={symbol}&tsym=USDT&limit={limit}&aggregate={ag[tf]}&e={ex}"
        if "h" in tf: url = url.replace("minute", "hour")
        if "d" in tf: url = url.replace("minute", "day")
        
        res = requests.get(url).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
    except: return None
    return None

# --- SIDEBAR (Админка как на скриншотах) ---
with st.sidebar:
    st.title("👤 admin")
    st.session_state.balance = st.number_input("Депозит ($)", value=st.session_state.balance)
    st.divider()
    
    st.subheader("➕ Новая сделка")
    with st.form("new_trade"):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Вход", value=0.0) # Пустые графы по твоему запросу
        qty = st.number_input("Кол-во", value=0.0)
        sl = st.number_input("Стоп", value=0.0)
        tp = st.number_input("Тейк", value=0.0)
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            st.session_state.trades.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "coin": coin, "side": side, "entry": entry,
                "qty": qty, "sl": sl, "tp": tp
            })
            st.rerun()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    # Верхняя строка управления
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: cur_coin = st.text_input("Тикер", "BTC").upper()
    with c2: cur_market = st.selectbox("Рынок", ["SPOT", "FUTURES"])
    with c3:
        st.write("Таймфрейм")
        tfs = st.columns(5)
        tf_list = ["5m", "15m", "1h", "4h", "1d"]
        selected_tf = "15m"
        for i, f in enumerate(tf_list):
            if tfs[i].button(f): selected_tf = f

    # Получаем данные
    df = get_data(cur_coin, selected_tf, cur_market)
    
    if df is not None:
        last_price = df['close'].iloc[-1]
        
        # Метрики как на скриншоте 18:41
        m1, m2, m3 = st.columns(3)
        m1.metric("Цена", f"${last_price:,.2f}")
        m2.metric("P/L", "$0.00")
        m3.metric("Активных", len(st.session_state.trades))

        # График
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], 
            low=df['low'], close=df['close']
        )])
        
        # Линии сделок
        for t in st.session_state.trades:
            if t['coin'] == cur_coin:
                fig.add_hline(y=t['entry'], line_color="white", annotation_text="Вход")
        
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Ожидание данных...")

    st.subheader("📈 Кривая доходности")
    st.info("Нет закрытых сделок для построения графика.")

with tab_journal:
    st.subheader("Список открытых позиций")
    if st.session_state.trades:
        for i, t in enumerate(st.session_state.trades):
            col = st.columns([1, 1, 1, 1, 1, 0.5])
            col[0].write(f"{t['time']}")
            col[1].write(f"**{t['coin']} ({t['side']})**")
            col[2].write(f"Вход: {t['entry']}")
            col[3].write(f"SL: {t['sl']}")
            col[4].write(f"TP: {t['tp']}")
            if col[5].button("🗑", key=f"del_{i}"):
                st.session_state.trades.pop(i)
                st.rerun()
    else:
        st.write("Сделок нет")
