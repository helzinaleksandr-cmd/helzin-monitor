import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Helzin Pro Terminal", layout="wide")

# --- СИСТЕМА ВХОДА И РЕГИСТРАЦИИ ---
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def auth_ui():
    st.title("🔐 Helzin Terminal: Вход")
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    with tab1:
        u = st.text_input("Логин")
        p = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Ошибка входа")
    with tab2:
        new_u = st.text_input("Новый логин")
        new_p = st.text_input("Новый пароль", type="password")
        if st.button("Создать аккаунт"):
            st.session_state.users[new_u] = new_p
            st.success("Готово! Войдите во вкладке рядом.")

# --- РАБОЧИЙ ТЕРМИНАЛ BINANCE ---
def terminal_ui():
    st.sidebar.write(f"👤 {st.session_state.user}")
    if st.sidebar.button("Выход"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🚀 Helzin Binance Live (Direct Feed)")
    symbol = st.sidebar.text_input("Тикер", "BTC").upper()
    
    if 'history' not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

    placeholder = st.empty()

    while True:
        try:
            # Берем цену Binance через открытый шлюз CryptoCompare
            url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&e=Binance"
            res = requests.get(url, timeout=5).json()
            price = res['USDT']
            now = datetime.now().strftime("%H:%M:%S")

            # Обновление данных
            new_row = pd.DataFrame({'Время': [now], 'Цена': [price]})
            st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]

            with placeholder.container():
                col1, col2 = st.columns([1, 2])
                col1.metric(f"Binance {symbol}/USDT", f"${price:,.2f}")
                col1.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
                col2.line_chart(st.session_state.history.set_index('Время'))

            time.sleep(2)
            st.rerun()
        except:
            st.warning("Синхронизация с Binance...")
            time.sleep(5)
            st.rerun()

# Логика переключения
if not st.session_state.logged_in:
    auth_ui()
else:
    terminal_ui()
    # Секретная панель менеджера (только для admin)
    if st.session_state.user == "admin":
        with st.sidebar.expander("🛠 ПАНЕЛЬ МЕНЕДЖЕРА"):
            st.write("Список зарегистрированных юзеров:")
            # Показываем всех пользователей и их пароли
            users_df = pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль'])
            st.table(users_df)
            
            if st.button("Очистить историю цен"):
                st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])
                st.rerun()
