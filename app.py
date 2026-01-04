import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Pro Live)")

# Боковая панель
symbol = st.sidebar.text_input("Тикер (со слешем)", "BTC/USDT").upper()

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

placeholder = st.empty()

@st.cache_resource
def get_exchange():
    # Настройка профессионального клиента для обхода блокировки 451
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True}
    })
    # Используем альтернативный шлюз, который чаще всего открыт для облаков
    exchange.urls['api']['public'] = 'https://api1.binance.com/api/3'
    return exchange

binance = get_exchange()

while True:
    try:
        # Пытаемся получить цену напрямую через профессиональный API
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Обновляем таблицу истории (последние 30 тиков)
        new_row = pd.DataFrame({'Время': [current_time], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-30:]
        
        with placeholder.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric(f"Binance: {symbol}", f"${price:,.2f}")
                st.write("### Журнал цен")
                st.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
            with col2:
                st.write("### График Real-time")
                st.line_chart(st.session_state.history.set_index('Время'))
                
        time.sleep(1) # Обновление каждую секунду
        st.rerun()
        
    except Exception as e:
        # Если Binance все же сбросил соединение, пробуем через 5 секунд
        st.warning("Переподключение к Binance... Поиск свободного шлюза.")
        time.sleep(5)
        st.rerun()
