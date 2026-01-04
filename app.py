import streamlit as st
import requests
import pandas as pd
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor")

# Боковая панель
symbol = st.sidebar.text_input("Тикер монеты", "BTCUSDT").upper()

# Инициализация истории цен в памяти сервера
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

placeholder = st.empty()

while True:
    try:
        # В облаке используем стандартный защищенный запрос к Binance
        url = f"https://api.binance.com/api/3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        price = float(data['price'])
        current_time = time.strftime("%H:%M:%S")
        
        # Обновляем данные (оставляем последние 20 точек)
        new_row = pd.DataFrame({'Время': [current_time], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
        
        # Отрисовка интерфейса
        with placeholder.container():
            st.metric(f"Цена {symbol}", f"${price:,.2f}")
            st.line_chart(st.session_state.history.set_index('Время'))
            st.table(st.session_state.history.iloc[::-1]) # Таблица в обратном порядке
            
        time.sleep(2)
    except Exception as e:
        st.error(f"Ошибка связи с Binance. Проверьте тикер или подождите...")
        time.sleep(5)
