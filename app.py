import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# Настройка интерфейса профессионального терминала
st.set_page_config(page_title="Helzin Binance Pro", layout="wide")
st.title("🚀 Helzin Market Monitor (Binance Pro Live)")

# Инициализация сессии для хранения данных
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])
if 'journal' not in st.session_state:
    st.session_state.journal = pd.DataFrame(columns=['Время', 'Тикер', 'Цена', 'Тип'])

# Боковая панель управления
st.sidebar.header("Настройки терминала")
symbol = st.sidebar.text_input("Тикер (формат BTC/USDT)", "BTC/USDT").upper()

# Профессиональное подключение через CCXT
@st.cache_resource
def get_binance():
    # Используем настройки для обхода блокировок облачных провайдеров
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True}
    })
    # Принудительно используем альтернативные API-шлюзы
    exchange.urls['api']['public'] = 'https://api1.binance.com/api/3'
    return exchange

client = get_binance()

# Основной интерфейс
col1, col2 = st.columns([2, 1])

placeholder = st.empty()

while True:
    try:
        # Получение данных в реальном времени
        ticker = client.fetch_ticker(symbol)
        price = ticker['last']
        now = datetime.now().strftime("%H:%M:%S")
        
        # Обновление графика
        new_data = pd.DataFrame({'Время': [now], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_data]).iloc[-30:]
        
        with placeholder.container():
            c1, c2 = st.columns(2)
            c1.metric(f"Текущая цена {symbol}", f"${price:,.2f}")
            c2.line_chart(st.session_state.history.set_index('Время'))
            
            st.write("### Журнал мониторинга")
            st.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
            
        time.sleep(1)
        st.rerun() # Живое обновление страницы
        
    except Exception as e:
        st.warning("Связь с Binance... Поиск свободного шлюза.")
        time.sleep(5)
        st.rerun()
