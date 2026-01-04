import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Pro Live)")

# Боковая панель
st.sidebar.header("Настройки")
symbol = st.sidebar.text_input("Тикер (со слешем)", "BTC/USDT").upper()

# Инициализация истории в памяти сессии
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# Контейнеры для живого обновления
metric_col = st.empty()
chart_col = st.empty()
table_col = st.empty()

# Инициализация Binance через CCXT с обходом блокировок
@st.cache_resource
def get_exchange():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True}
    })
    # Используем альтернативный шлюз, чтобы обойти ошибку 451
    exchange.urls['api']['public'] = 'https://api1.binance.com/api/3'
    return exchange

binance = get_exchange()

# Основной цикл работы
while True:
    try:
        # Получаем данные
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Добавляем в историю
        new_row = pd.DataFrame({'Время': [current_time], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-30:]
        
        # Отображаем данные
        with metric_col.container():
            st.metric(label=f"Текущая цена {symbol}", value=f"${price:,.2f}")
        
        with chart_col.container():
            st.line_chart(st.session_state.history.set_index('Время'))
            
        with table_col.container():
            st.write("Последние изменения:")
            st.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
            
        time.sleep(1) # Частота обновления — 1 секунда
        st.rerun() # Команда для живого обновления в облаке

    except Exception as e:
        st.warning(f"Подключение к шлюзу Binance... Проверьте формат тикера (например, BTC/USDT)")
        time.sleep(5)
        st.rerun()
        
