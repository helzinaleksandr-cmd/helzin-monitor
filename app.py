import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# 1. Базовая настройка (должна быть первой)
st.set_page_config(page_title="Helzin Terminal", layout="wide")

# 2. Инициализация хранилища
DB_FILE = "trades_history.json"

if 'trades' not in st.session_state:
    st.session_state.trades = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.trades = data.get("trades", [])
        except: st.error("Ошибка загрузки истории сделок")

if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0

def save_data():
    try:
        data = {"trades": st.session_state.trades, "deposit": st.session_state.deposit}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# 3. Работа с данными
def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=500&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        st.session_state.last_price = float(df['close'].iloc[-1])
        return df
    except: return None

# 4. Интерфейс терминала
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    if st.button("Войти в систему"): 
        st.session_state.logged_in = True
        st.rerun()
else:
    # --- САЙДБАР ---
    with st.sidebar:
        st.header("👤 admin")
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        st.subheader("➕ Новая сделка")
        
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin_in = st.text_input("Монета", value="BTC", autocomplete="off").upper()
        
        c_pr = st.session_state.last_price
        ent = st.text_input("Вход", value=str(c_pr) if c_pr > 0 else "", autocomplete="off")
        amt = st.text_input("Кол-во", autocomplete="off")
        sl = st.text_input("Стоп", autocomplete="off")
        tp = st.text_input("Тейк", autocomplete="off")
        
        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            try:
                e, a, s, tk = [float(x.replace(',','.')) for x in [ent, amt, sl, tp]]
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": side, "Монета": coin_in, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk, 
                    "RR": round(abs(tk-e)/abs(e-s), 2) if abs(e-s)>0 else 0,
                    "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                })
                save_data(); st.rerun()
            except: st.error("Ошибка в числах!")
        
        if st.button("Выход"): 
            st.session_state.
