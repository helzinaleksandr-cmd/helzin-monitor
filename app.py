import streamlit as st
import requests
import time
import pandas as pd

st.set_page_config(page_title="Helzin Monitor", layout="wide")
st.title("📊 Helzin Market Monitor")

symbol = st.sidebar.text_input("Тикер монеты", "BTCUSDT").upper()
price_metric = st.empty()

if 'price_history' not in st.session_state:
    st.session_state.price_history = []

while True:
    try:
        url = f"https://api.binance.com/api/3/ticker/24hr?symbol={symbol}"
        res = requests.get(url).json()
        current_p = float(res['lastPrice'])
        
        price_metric.metric("Цена", f"${current_p:,.2f}")
        
        new_row = {"Время": time.strftime("%H:%M:%S"), "Цена": current_p}
        st.session_state.price_history.insert(0, new_row)
        if len(st.session_state.price_history) > 10:
            st.session_state.price_history.pop()
            
        st.table(pd.DataFrame(st.session_state.price_history))
        time.sleep(2)
    except:
        st.error("Связь с Binance...")
        time.sleep(5)
