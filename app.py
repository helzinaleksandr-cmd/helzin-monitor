import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# Настройки страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация данных (база пользователей и история)
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# --- ЭКРАН ВХОДА ---
def auth_ui():
    st.title("🔐 Вход в Helzin Pro")
    tab_log, tab_reg = st.tabs(["Вход", "Регистрация юзера"])
    
    with tab_log:
        u = st.text_input("Логин", key="login_u")
        p = st.text_input("Пароль", type="password", key="login_p")
        if st.button("Войти в терминал"):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Неверный логин или пароль")
    
    with tab_reg:
        new_u = st.text_input("Придумайте логин", key="reg_u")
        new_p = st.text_input("Придумайте пароль", type="password", key="reg_p")
        if st.button("Создать аккаунт"):
            if new_u and new_p:
                st.session_state.users[new_u] = new_p
                st.success("Аккаунт создан! Теперь войдите.")

# --- РАБОЧИЙ ТЕРМИНАЛ ---
def terminal_ui():
    # Кнопка выхода в углу
    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()

    st.title(f"🚀 Добро пожаловать, {st.session_state.user}!")
    
    # Создаем вкладки
    tab1, tab2, tab3 = st.tabs(["📊 Мониторинг", "👥 Менеджер юзеров", "📂 О системе"])

    with tab1:
        st.subheader("Живая цена Binance")
        symbol = st.text_input("Тикер (BTC, ETH, SOL)", "BTC").upper()
        
        # Контейнеры для графиков
        col1, col2 = st.columns([1, 2])
        price_spot = col1.empty()
        table_spot = col1.empty()
        chart_spot = col2.empty()

        # Запускаем цикл обновления прямо здесь
        while True:
            try:
                # Берем цену
                url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&e=Binance"
                res = requests.get(url, timeout=5).json()
                price = res['USDT']
                now = datetime.now().strftime("%H:%M:%S")

                # Обновляем историю
                new_data = pd.DataFrame({'Время': [now], 'Цена': [price]})
                st.session_state.history = pd.concat([st.session_state.history, new_data]).iloc[-20:]
                
                # Показываем данные
                price_spot.metric(f"Binance {symbol}/USDT", f"${price:,.2f}")
                table_spot.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
                chart_spot.line_chart(st.session_state.history.set_index('Время'))
                
                time.sleep(2)
            except:
                st.warning("Синхронизация...")
                time.sleep(2)

    with tab2:
        st.subheader("Список зарегистрированных лиц")
        if st.session_state.user == "admin":
            st.table(pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль']))
        else:
            st.error("Доступ только для менеджера.")

    with tab3:
        st.info("Helzin Terminal v1.0 — Профессиональный инструмент мониторинга.")

# Главная логика запуска
if not st.session_state.logged_in:
    auth_ui()
else:
    terminal_ui()
