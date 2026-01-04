import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# Настройка интерфейса
st.set_page_config(page_title="Helzin Binance Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Pro Live)")

# Боковая панель управления
st.sidebar.header("Настройки")
symbol = st.sidebar.text_input("Тикер (например, BTC/USDT)", "BTC/USDT").upper()

# Инициализация истории в памяти сессии
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# Контейнеры для отображения (чтобы страница не "прыгала")
placeholder = st.empty()

# Функция для создания стабильного подключения
@st.cache_resource
def get_exchange():
    # Мы используем CCXT, так как она лучше всех справляется с прокси и шлюзами
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True}
    })
    # Список резервных шлюзов Binance
    exchange.urls['api']['public'] = 'https://api1.binance.com/api/3'
    return exchange

binance = get_exchange()

while True:
    try:
        # Получаем данные о цене
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Обновляем DataFrame истории (последние 30 тиков)
        new_row = pd.DataFrame({'Время': [current_time], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_row]).iloc[-30:]
        
        # Визуализация данных
        with placeholder.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.metric(label=f"Live Price {symbol}", value=f"${price:,.2f}")
                st.write("### Лента сделок")
                st.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
                
            with col2:
                st.write("### График изменений")
                st.line_chart(st.session_state.history.set_index('Время'))
        
        # Задержка 1 секунда для реального времени
        time.sleep(1)
        st.rerun() # Перезапуск скрипта для обновления данных
        
    except Exception as e:
        # Если api1 недоступен, пробуем api2 или api3
        st.warning("Поиск свободного шлюза Binance... Пожалуйста, подождите.")
        time.sleep(5)
        st.rerun()
        
