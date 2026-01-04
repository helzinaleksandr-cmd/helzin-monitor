import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация сессии
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'deposit' not in st.session_state:
    st.session_state.deposit = 1000.0

def get_crypto_data(ticker, tf):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=100&aggregate={aggregate}&e=Binance"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except:
        return None

if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u == "admin" and p == "12345":
            st.session_state.logged_in = True
            st.rerun()
else:
    with st.sidebar:
        st.header(f"👤 admin")
        st.session_state.deposit = st.number_input("Ваш Депозит ($)", value=float(st.session_state.deposit), format="%.2f")
        
        st.divider()
        st.subheader("➕ Новая сделка")
        
        t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        t_coin = st.text_input("Монета", "BTC").upper()
        
        temp_df = get_crypto_data(t_coin, "5m")
        curr_p = temp_df['close'].iloc[-1] if temp_df is not None else 0.0
        
        t_entry = st.number_input("Цена входа", value=float(curr_p), format="%.2f")
        t_amount = st.number_input("Кол-во монет", value=None, placeholder="0.00", format="%.4f", key="amt")
        t_stop = st.number_input("Уровень СТОП", value=None, placeholder="0.00", format="%.2f", key="sl")
        t_take = st.number_input("Уровень ТЕЙК", value=None, placeholder="0.00", format="%.2f", key="tp")
        
        # Расчет RR и P/L
        rr_val = 0.0
        potential_profit = 0.0
        potential_loss = 0.0
        
        if t_entry and t_stop and t_take and t_amount:
            if t_side == "LONG":
                risk_per_coin = t_entry - t_stop
                reward_per_coin = t_take - t_entry
            else:
                risk_per_coin = t_stop - t_entry
                reward_per_coin = t_entry - t_take
            
            potential_profit = reward_per_coin * t_amount
            potential_loss = risk_per_coin * t_amount
            
            if risk_per_coin > 0:
                rr_val = reward_per_coin / risk_per_coin
                st.info(f"📊 RR: 1 к {rr_val:.2f} | Риск: -{potential_loss:.2f}$ | Тейк: +{potential_profit:.2f}$")

        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if t_stop and t_take and t_amount:
                new_trade = {
                    "id": datetime.now().timestamp(),
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": t_side, "Монета": t_coin, "Кол-во": t_amount,
                    "Вход": t_entry, "Стоп": t_stop, "Тейк": t_take, 
                    "RR": round(rr_val, 2),
                    "Profit": round(potential_profit, 2),
                    "Loss": round(potential_loss, 2),
                    "Статус": "OPEN"
                }
                st.session_state.trades.append(new_trade)
                st.rerun()
            else:
                st.error("Заполни все поля!")

    tab1, tab2 = st.tabs(["🕯 График", "📑 Журнал сделок"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="m_t").upper()
        active_tf = c2.select_slider("Таймфрейм", options=["5m", "15m", "1h", "4h", "1d"], value="15m")
        df =
