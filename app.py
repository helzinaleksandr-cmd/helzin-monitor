import streamlit as st
import ccxt
import pandas as pd
import time

st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Pro)")

symbol = st.sidebar.text_input("Тикер Binance", "BTC/USDT").upper()

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# Инициализация биржи (ccxt сама выберет лучший путь)
exchange = ccxt.binance({
    'enableRateLimit': True,
})

placeholder = st.empty()

while True:
    try:
        # Получаем данные через профессиональный шлюз
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        # Обновляем историю
        new_row = pd.DataFrame({'Время': [time.strftime("%H:%M:%S")], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-20:]
        
        with placeholder.container():
            st.metric(f"Binance Live: {symbol}", f"${price:,.2f}")
            st.line_chart(st.session_state.history.set_index('Время'))
            st.table(st.session_state.history.iloc[::-1])
            
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error(f"Поиск стабильного шлюза Binance... Проверьте тикер (формат BTC/USDT)")
        time.sleep(5)
        st.rerun()
