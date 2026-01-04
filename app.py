import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Helzin Terminal", layout="wide")
st.title("🚀 Helzin Market Monitor")

symbol = st.sidebar.text_input("Тикер монеты", "BTCUSDT").upper()

# Контейнеры для данных
price_placeholder = st.empty()
chart_placeholder = st.empty()

# Функция получения данных
def get_price(sym):
    try:
        # Используем api1 для надежности
        url = f"https://api1.binance.com/api/3/ticker/price?symbol={sym}"
        res = requests.get(url, timeout=5)
        return float(res.json()['price'])
    except:
        return None

# Инициализация истории
if 'history' not in st.session_state:
    st.session_state.history = []

# Цикл обновления
price = get_price(symbol)
if price:
    st.session_state.history.append(price)
    if len(st.session_state.history) > 30:
        st.session_state.history.pop(0)

    price_placeholder.metric(f"Цена {symbol}", f"${price:,.2f}")
    chart_placeholder.line_chart(st.session_state.history)
    
    # Авто-обновление страницы каждые 2 секунды
    time.sleep(2)
    st.rerun()
else:
    st.error("Ошибка связи с Binance. Проверьте тикер!")
    time.sleep(5)
    st.rerun()
