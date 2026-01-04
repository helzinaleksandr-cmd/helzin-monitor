import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Helzin Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor")

# Настройки в боковой панели
st.sidebar.info("Для крипты используйте формат: BTC-USD, ETH-USD")
symbol = st.sidebar.text_input("Тикер монеты", "BTC-USD").upper()

if 'history' not in st.session_state:
    st.session_state.history = []

placeholder = st.empty()

while True:
    try:
        # Получаем данные из Yahoo Finance (очень стабильно для облака)
        data = yf.Ticker(symbol).history(period="1d", interval="1m")
        if not data.empty:
            price = data['Close'].iloc[-1]
            st.session_state.history.append(price)
            
            # Ограничиваем историю 30 точками
            if len(st.session_state.history) > 30:
                st.session_state.history.pop(0)

            with placeholder.container():
                st.metric(f"Цена {symbol} (Yahoo)", f"${price:,.2f}")
                st.line_chart(st.session_state.history)
        
        time.sleep(10) # Yahoo не любит слишком частые запросы, 10 сек — идеально
        st.rerun()
    except Exception as e:
        st.error(f"Служба поиска данных временно недоступна. Попробуем снова...")
        time.sleep(10)
        st.rerun()
