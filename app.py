import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Настройки оформления
st.set_page_config(page_title="Helzin Pro Terminal", layout="wide")

# База пользователей
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

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

# --- ИНТЕРФЕЙС ---
if not st.session_state.logged_in:
    st.title("🔐 Вход в систему")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()
else:
    # Меню слева
    if st.sidebar.button("Выход"):
        st.session_state.logged_in = False
        st.rerun()

    tab1, tab2 = st.tabs(["🕯 График Binance", "👥 Менеджер"])

    with tab1:
        symbol = st.text_input("Тикер", "BTC").upper()
        df = get_candlesticks(symbol)
        
        if df is not None:
            price = df['close'].iloc[-1]
            st.metric(f"Текущая цена {symbol}/USDT", f"${price:,.2f}")

            # РИСУЕМ СВЕЧИ (они не дают "синий экран")
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])

            fig.update_layout(
                template="plotly_dark",
                height=600,
                xaxis_rangeslider_visible=False,
                yaxis=dict(autorange=True, fixedrange=False) # Авто-масштаб по цене!
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("Обновить график"):
                st.rerun()
        else:
            st.error("Ошибка получения данных")

    with tab2:
        if st.session_state.user == "admin":
            st.write("### Зарегистрированные юзеры")
            st.table(pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль']))
