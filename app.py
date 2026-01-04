import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация состояния
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0
if 'price' not in st.session_state:
    st.session_state.price = 0.0
if 'tf' not in st.session_state:
    st.session_state.tf = "1h"

# Словарь ID монет для CoinGecko (можно добавлять новые)
COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "TON": "toncoin",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "MATIC": "polygon",
    "LTC": "litecoin",
    "DOT": "polkadot"
}

# Функция получения данных с CoinGecko (бесплатно, без ключей)
def get_data(symbol, tf):
    symbol = symbol.upper()
    if symbol not in COINGECKO_IDS:
        return None, 0.0

    coin_id = COINGECKO_IDS[symbol]

    # Количество дней данных в зависимости от таймфрейма
    if tf in ["5m", "15m"]:
        days = 1
        interval = "hourly"
