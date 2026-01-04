import streamlit as st
import pandas as pd
import time
import json
from websocket import create_connection

st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Live)")

symbol = st.sidebar.text_input("Тикер Binance", "BTCUSDT").lower()

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

placeholder = st.empty()

# Используем WebSocket - он пробивает блокировки 451
ws_url = f"wss://stream.binance.com:9443/ws/{symbol}@ticker"

def stream_data():
    try:
        ws = create_connection(ws_url)
        while True:
            result = ws.recv()
            data = json.loads(result)
            price = float(data['c']) # 'c' - это текущая цена в Binance WS
            
            # Обновляем данные
            new_row = pd.DataFrame({'Время': [time.strftime("%H:%M:%S")], 'Цена': [price]})
            st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
            
            with placeholder.container():
                st.metric(f"Binance Live: {symbol.upper()}", f"${price:,.2f}")
                st.line_chart(st.session_state.history.set_index('Время'))
                st.table(st.session_state.history.iloc[::-1])
            
            time.sleep(1) # Обновление каждую секунду!
    except Exception as e:
        st.error(f"Переподключение к Binance...")
        time.sleep(5)
        st.rerun()

stream_data()
