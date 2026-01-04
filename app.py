import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="Helzin Pro Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor (Global Feed)")

# 2. Инициализация истории
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Время', 'Цена'])

# 3. Настройка биржи (используем Bybit, так как она открыта для облака)
@st.cache_resource
def get_exchange():
    return ccxt.bybit({'enableRateLimit': True})

client = get_exchange()

# 4. Интерфейс
symbol = st.sidebar.text_input("Тикер (BTC/USDT)", "BTC/USDT").upper()
placeholder = st.empty()

# 5. Главный цикл получения цены
while True:
    try:
        # Получаем данные
        ticker = client.fetch_ticker(symbol)
        price = ticker['last']
        now = datetime.now().strftime("%H:%M:%S")
        
        # Обновляем историю (храним 30 точек)
        new_data = pd.DataFrame({'Время': [now], 'Цена': [price]})
        st.session_state.history = pd.concat([st.session_state.history, new_data]).iloc[-30:]
        
        # Отрисовка данных
        with placeholder.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric(f"Live Price {symbol}", f"${price:,.2f}")
                st.write("### Лента цен")
                st.dataframe(st.session_state.history.iloc[::-1], use_container_width=True)
            with col2:
                st.write("### График")
                st.line_chart(st.session_state.history.set_index('Время'))
                
        time.sleep(1) # Обновление каждую секунду
        st.rerun() # Перезапуск для свежих данных
        
    except Exception as e:
        st.warning(f"Подключение к глобальному шлюзу... Проверьте тикер.")
        time.sleep(5)
        st.rerun()
