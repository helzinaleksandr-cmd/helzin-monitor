import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Настройки оформления
st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация данных
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = []

# Функция получения данных с разными ТФ
def get_crypto_data(ticker, tf):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map[tf]
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=100&aggregate={aggregate}&e=Binance"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except:
        return None

# --- ВХОД В СИСТЕМУ ---
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()
else:
    # --- ЛЕВАЯ КОЛОНКА (УПРАВЛЕНИЕ) ---
    with st.sidebar:
        st.header(f"👤 {st.session_state.user}")
        
        st.subheader("➕ Новая сделка")
        # Группируем ввод данных строго слева
        t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        t_coin = st.text_input("Монета", "BTC").upper()
        t_entry = st.number_input("Вход", value=0.0, format="%.2f")
        t_stop = st.number_input("Стоп", value=0.0, format="%.2f")
        t_take = st.number_input("Тейк", value=0.0, format="%.2f")
        
        if st.button("Открыть позицию", use_container_width=True):
            st.session_state.trades.append({
                "Время": datetime.now().strftime("%H:%M:%S"),
                "Тип": t_side, "Монета": t_coin, "Вход": t_entry, 
                "Стоп": t_stop, "Тейк": t_take, "Статус": "OPEN"
            })
            st.success("Сделка добавлена!")
        
        st.divider()
        if st.button("Выход", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- ОСНОВНАЯ ЧАСТЬ (ГРАФИК И ЖУРНАЛ) ---
    tab1, tab2 = st.tabs(["🕯 График и Аналитика", "📑 Журнал сделок"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        active_coin = c1.text_input("Поиск тикера", "BTC").upper()
        active_tf = c2.select_slider("Таймфрейм", options=["5m", "15m", "1h", "4h", "1d"], value="15m")
        
        df = get_crypto_data(active_coin, active_tf)
        if df is not None:
            price = df['close'].iloc[-1]
            st.metric(f"Цена {active_coin}/USDT ({active_tf})", f"${price:,.2f}")
            
            # Профессиональный график
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
                             yaxis=dict(autorange=True, fixedrange=False), margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Ошибка загрузки данных Binance")

    with tab2:
        st.subheader("Ваши позиции")
        if st.session_state.trades:
            # Вывод таблицы сделок
            df_trades = pd.DataFrame(st.session_state.trades)
            st.dataframe(df_trades.iloc[::-1], use_container_width=True)
            if st.button("Очистить все сделки"):
                st.session_state.trades = []
                st.rerun()
        else:
            st.info("Сделок пока не зафиксировано")
