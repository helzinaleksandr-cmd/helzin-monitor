import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Helzin Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor")

# Настройки
symbol = st.sidebar.text_input("Тикер", "BTCUSDT").upper()

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

placeholder = st.empty()

while True:
    try:
        # В облаке мы используем стандартный защищенный запрос
        url = f"https://api.binance.com/api/3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        price = float(data['price'])
        
        # Обновляем таблицу
        new_row = pd.DataFrame({'Время': [time.strftime("%H:%M:%S")], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
        
        with placeholder.container():
            st.metric(f"Текущая цена {symbol}", f"${price:,.2f}")
            st.line_chart(st.session_state.history.set_index('Время'))
            st.table(st.session_state.history.iloc[::-1])
            
        time.sleep(2)
    except Exception as e:
        st.error(f"Ошибка получения данных. Проверьте тикер {symbol}")
        time.sleep(5)
