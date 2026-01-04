import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Настройки страницы
st.set_page_config(page_title="Helzin Pro Terminal", layout="wide")

# Инициализация (база пользователей)
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ИСТОРИИ (КАК НА БИРЖЕ) ---
def get_binance_history(ticker):
    try:
        # Запрашиваем последние 100 минут истории с Binance через шлюз
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={ticker}&tsym=USDT&limit=100&e=Binance"
        res = requests.get(url, timeout=5).json()
        data = res['Data']['Data']
        df = pd.DataFrame(data)
        # Превращаем время в понятный формат
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df[['time', 'close']]
    except:
        return None

# --- ЭКРАН ВХОДА ---
def auth_ui():
    st.title("🔐 Helzin Terminal: Авторизация")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()

# --- ИНТЕРФЕЙС ТЕРМИНАЛА ---
def terminal_ui():
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.rerun()
    
    tab1, tab2 = st.tabs(["📊 Биржевой график", "👥 Менеджер"])

    with tab1:
        st.subheader("Аналитика рынка в реальном времени")
        symbol = st.text_input("Тикер (BTC, ETH, SOL)", "BTC").upper()
        
        # Получаем исторические данные
        history_df = get_binance_history(symbol)
        
        if history_df is not None:
            current_price = history_df['close'].iloc[-1]
            st.metric(f"Текущая цена {symbol}/USDT (Binance)", f"${current_price:,.2f}")
            
            # РИСУЕМ ГРАФИК С ИСТОРИЕЙ
            st.write("### История цены (последние 100 минут)")
            st.area_chart(history_df.set_index('time')) # Area chart выглядит солиднее
            
            st.write("### Таблица котировок")
            st.dataframe(history_df.iloc[::-1], use_container_width=True)
        else:
            st.error("Не удалось подгрузить историю. Проверьте тикер.")
        
        if st.button("Обновить данные"):
            st.rerun()

    with tab2:
        if st.session_state.user == "admin":
            st.table(pd.DataFrame(list(st.session_state.users.items()), columns=['Логин', 'Пароль']))

# Запуск
if not st.session_state.logged_in:
    auth_ui()
else:
    terminal_ui()
