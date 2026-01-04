import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Настройки страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация базы пользователей и состояния входа
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# --- ЭКРАН ВХОДА ---
def auth_ui():
    st.title("🔐 Авторизация в Helzin Pro")
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])
    
    with tab_login:
        u = st.text_input("Логин", key="l_u")
        p = st.text_input("Пароль", type="password", key="l_p")
        if st.button("Войти"):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Ошибка: проверьте логин и пароль")
                
    with tab_register:
        new_u = st.text_input("Новый логин", key="r_u")
        new_p = st.text_input("Новый пароль", type="password", key="r_p")
        if st.button("Зарегистрироваться"):
            if new_u and new_p:
                st.session_state.users[new_u] = new_p
                st.success("Аккаунт создан успешно! Перейдите во вкладку 'Вход'.")

# --- ОСНОВНОЙ ИНТЕРФЕЙС ТЕРМИНАЛА ---
def terminal_ui():
    # Боковая панель
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Кнопка ручного обновления и авто-обновление каждые 2 секунды
    st.sidebar.divider()
    if st.sidebar.button("Обновить цену вручную"):
        st.rerun()

    # СОЗДАНИЕ ВКЛАДОК
    tab_monitor, tab_admin, tab_about = st.tabs(["📊 Мониторинг", "👥 Менеджер", "📂 Инфо"])

    with tab_monitor:
        st.subheader("Живые котировки Binance")
        symbol = st.text_input("Тикер", "BTC").upper()
        
        try:
            # Получение цены
            url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&e=Binance"
            res = requests.get(url, timeout=5).json()
            price = res['USDT']
            now = datetime.now().strftime("%H:%M:%S")
            
            # Обновление истории
            new_data = pd.DataFrame({'Время': [now], 'Цена': [price]})
            st.session_state.history = pd.concat([st.session_state.history, new_data]).iloc[-20:]
            
            # Отрисовка
            c1, c2 = st.columns([1, 2])
            c1.metric(f"{symbol}/USDT", f"${price:,.2f}")
            c1.write("### Последние изменения")
            c1.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
            c2.write("### График")
            c2.line_chart(st.session_state.history.set_index('Время'))
            
        except Exception as e:
            st.warning("Ожидание данных с Binance...")

    with tab_admin:
        st.subheader("Управление пользователями")
        if st.session_state.user == "admin":
            st.write("База данных клиентов:")
            u_df = pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль'])
            st.table(u_df)
        else:
            st.error("У вас нет прав администратора")

    with tab_about:
        st.info("Helzin Terminal v1.1 — Система мониторинга с модулем регистрации.")

# Запуск приложения
if not st.session_state.logged_in:
    auth_ui()
else:
    terminal_ui()
