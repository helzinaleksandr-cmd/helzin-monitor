import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Live)")

symbol = st.sidebar.text_input("Тикер Binance", "BTCUSDT").upper()

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

placeholder = st.empty()

# Специальные заголовки, чтобы Binance не блокировал облачный сервер
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

while True:
    try:
        # Пытаемся подключиться через альтернативный шлюз api3
        url = f"https://api3.binance.com/api/3/ticker/price?symbol={symbol}"
        response = requests.get(url, headers=headers, timeout=10)
        
      if response.status_code == 200:
            data = response.json()
            price = float(data['price'])
            
            new_row = pd.DataFrame({'Время': [time.strftime("%H:%M:%S")], 'Цена': [price]})
            st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
            
            with placeholder.container():
                st.metric(f"Binance Live: {symbol}", f"${price:,.2f}")
                st.line_chart(st.session_state.history.set_index('Время'))
                st.table(st.session_state.history.iloc[::-1])
        else:
            st.error(f"Binance ответил кодом {response.status_code}. Пробуем пробиться...")
            
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error("Поиск шлюза Binance... Пожалуйста, подождите.")
        time.sleep(5)
        st.rerun()
