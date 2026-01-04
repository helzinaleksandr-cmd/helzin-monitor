import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# 1. Глобальные настройки интерфейса
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# 2. Инициализация базы пользователей и истории (в памяти сессии)
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ДАННЫХ ---
def get_binance_price(ticker):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={ticker}&tsyms=USDT&e=Binance"
        res = requests.get(url, timeout=5).json()
        return res['USDT']
    except:
        return None

# --- ЭКРАН ВХОДА ---
def auth_ui():
    st.title("🔐 Helzin Pro: Авторизация")
    tab1, tab2 = st.tabs(["Вход в систему", "Регистрация нового юзера"])
    
    with tab1:
        u = st.text_input("Логин", key="login_user")
        p = st.text_input("Пароль", type="password", key="login_pass")
        if st.button("Войти"):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Неверные данные доступа")

    with tab2:
        st.info("Здесь новые пользователи могут создать аккаунт")
        new_u = st.text_input("Придумайте логин", key="reg_user")
        new_p = st.text_input("Придумайте пароль", type="password", key="reg_pass")
        if st.button("Зарегистрироваться"):
            if new_u and new_p:
                st.session_state.users[new_u] = new_p
                st.success("Регистрация успешна! Теперь перейдите во вкладку 'Вход'")
            else:
                st.warning("Заполните все поля")

# --- ОСНОВНОЙ ТЕРМИНАЛ ---
def terminal_ui():
    # Навигация в боковой панели
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()

    # Главные вкладки сайта
    tab_main, tab_admin, tab_info = st.tabs(["📊 Мониторинг", "👥 Управление", "📂 О проекте"])

    with tab_main:
        st.subheader("Живой поток данных Binance")
        symbol = st.text_input("Тикер (например, BTC, ETH, SOL)", "BTC").upper()
        
        # Контейнеры для обновления
        metric_col, chart_col = st.columns([1, 2])
        price_placeholder = metric_col.empty()
        table_placeholder = metric_col.empty()
        chart_placeholder = chart_col.empty()

        # Цикл обновления данных
        while True:
            price = get_binance_price(symbol)
            if price:
                now = datetime.now().strftime("%H:%M:%S")
                new_row = pd.DataFrame({'Время': [now], 'Цена': [price]})
                st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
                
                price_placeholder.metric(f"Binance {symbol}/USDT", f"${price:,.2f}")
                table_placeholder.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
                chart_placeholder.line_chart(st.session_state.history.set_index('Время'))
            
            time.sleep(1)
            # Мы не используем rerun внутри while True здесь, чтобы вкладки работали стабильно

    with tab_admin:
        st.subheader("Панель управления менеджера")
        if st.session_state.user == "admin":
            st.write("Список всех зарегистрированных пользователей:")
            users_list = pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль'])
            st.table(users_list)
        else:
            st.error("Доступ только для администратора")
