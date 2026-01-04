import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Настройки оформления
st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация базы данных (в памяти)
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = [] # Список сделок

# Функция получения свечей
def get_candlesticks(ticker):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={ticker}&tsym=USDT&limit=60&e=Binance"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except:
        return None

# --- АВТОРИЗАЦИЯ ---
if not st.session_state.logged_in:
    st.title("🚀 Helzin Terminal: Вход")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()
else:
    # --- ТЕРМИНАЛ ---
    st.sidebar.write(f"👤 Менеджер: **{st.session_state.user}**")
    
    # КНОПКА НОВОЙ СДЕЛКИ В САЙДБАРЕ
    with st.sidebar.expander("➕ НОВАЯ СДЕЛКА", expanded=True):
        t_coin = st.text_input("Монета", "BTC").upper()
        t_entry = st.number_input("Цена входа", value=0.0, format="%.2f")
        t_stop = st.number_input("Стоп-лосс", value=0.0, format="%.2f")
        t_take = st.number_input("Тейк-профит", value=0.0, format="%.2f")
        if st.button("Открыть позицию"):
            trade_data = {
                "Время": datetime.now().strftime("%H:%M:%S"),
                "Монета": t_coin,
                "Вход": t_entry,
                "Стоп": t_stop,
                "Тейк": t_take,
                "Статус": "OPEN"
            }
            st.session_state.trades.append(trade_data)
            st.success(f"Сделка по {t_coin} открыта!")

    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()

    tab1, tab2 = st.tabs(["🕯 Торговый график", "📑 Журнал сделок"])

    with tab1:
        symbol = st.text_input("Поиск монеты", "BTC").upper()
        df = get_candlesticks(symbol)
        
        if df is not None:
            price = df['close'].iloc[-1]
            st.metric(f"Live {symbol}/USDT (Binance)", f"${price:,.2f}")

            # Профессиональные свечи
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])

            fig.update_layout(
                template="plotly_dark", height=500,
                xaxis_rangeslider_visible=False,
                yaxis=dict(autorange=True, fixedrange=False),
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("Обновить"):
                st.rerun()

    with tab2:
        st.subheader("Активные и закрытые сделки")
        if st.session_state.trades:
            trades_df = pd.DataFrame(st.session_state.trades)
            st.dataframe(trades_df.iloc[::-1], use_container_width=True) # Новые сверху
            if st.button("Очистить журнал"):
                st.session_state.trades = []
                st.rerun()
        else:
            st.info("У вас пока нет открытых сделок.")
