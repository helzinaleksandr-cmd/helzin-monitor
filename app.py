import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Ultimate", layout="wide")

# 1. Инициализация памяти (Баланс, Сделки)
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0

# 2. Функция получения данных (Упрощенная и надежная)
def get_crypto_data(symbol, tf, market):
    # Выбираем биржу в зависимости от рынка
    exchange = "BinanceFutures" if market == "FUTURES" else "Binance"
    # Настройка интервалов
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    limit = 100
    
    try:
        # Прямой запрос к API без лишних надстроек
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={symbol}&tsym=USDT&limit={limit}&aggregate={ag.get(tf, 15)}&e={exchange}"
        if "h" in tf: url = url.replace("minute", "hour")
        if "d" in tf: url = url.replace("minute", "day")
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            # Сохраняем последнюю цену
            st.session_state.price = float(df['close'].iloc[-1])
            return df
    except Exception as e:
        return None
    return None

# --- БОКОВАЯ ПАНЕЛЬ (Admin) ---
with st.sidebar:
    st.title("👤 admin")
    # Поле депозита как на скриншоте 19:29
    st.session_state.balance = st.number_input("Депозит ($)", value=st.session_state.balance, step=10.0)
    st.divider()
    
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # Поля пустые по умолчанию, как ты просил
        entry = st.number_input("Вход", value=0.0, format="%.2f")
        qty = st.number_input("Кол-во монет", value=0.0)
        sl = st.number_input("Стоп", value=0.0, format="%.2f")
        tp = st.number_input("Тейк", value=0.0, format="%.2f")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if qty > 0:
                # Расчет RR
                rr = round(abs(tp - entry) / abs(entry - sl), 2) if (entry - sl) != 0 else 0
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin, "side": side, "entry": entry,
                    "qty": qty, "sl": sl, "tp": tp, "rr": rr, "status": "В процессе ⏳"
                })
                st.rerun()

# --- ОСНОВНОЙ ЭКРАН ---
tab1, tab2 = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab1:
    # Панель управления
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: ticker = st.text_input("Тикер", "BTC").upper()
    with c2: m_type = st.selectbox("Рынок", ["FUTURES", "SPOT"])
    with c3:
        st.write("Таймфрейм")
        t_cols = st.columns(5)
        selected_tf = st.session_state.get('tf_choice', "15m")
        for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
            if t_cols[i].button(f, key=f): 
                st.session_state.tf_choice = f
                st.rerun()

    # Получение данных и отрисовка
    df = get_crypto_data(ticker, st.session_state.get('tf_choice', "15m"), m_type)
    current_p = st.session_state.price

    # Метрики (как на скриншотах 18:59)
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Текущая цена", f"${current_p:,.2f}")
    m_col2.metric("Депозит", f"${st.session_state.balance:,.2f}")
    m_col3.metric("Активных сделок", len([t for t in st.session_state.trades if "⏳" in t['status']]))

    if df is not None:
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Ошибка загрузки данных. Проверьте тикер или интернет.")

with tab2:
    st.subheader("📓 Журнал сделок")
    if st.session_state.trades:
        # Таблица (как на скриншоте 19:29)
        h_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 0.5])
        headers = ["Время", "Монета", "Тип", "Вход", "Стоп", "Тейк", "RR", "Статус", ""]
        for col, h in zip(h_cols, headers): col.write(f"**{h}**")
        
        for i, t in enumerate(st.session_state.trades):
            r_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 0.5])
            r_cols[0].write(t['time'])
            r_cols[1].write(t['coin'])
            r_cols[2].write(t['side'])
            r_cols[3].write(t['entry'])
            r_cols[4].write(t['sl'])
            r_cols[5].write(t['tp'])
            r_cols[6].write(f"**{t['rr']}**")
            r_cols[7].write(t['status'])
            if r_cols[8].button("🗑", key=f"del_{i}"):
                st.session_state.trades.pop(i)
                st.rerun()
    else:
        st.info("Сделок нет.")
