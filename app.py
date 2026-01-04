import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация данных
if 'users' not in st.session_state:
    st.session_state.users = {"admin": "12345"}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = []

def get_crypto_data(ticker, tf):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map[tf]
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=100&aggregate={aggregate}&e=Binance"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except:
        return None

# --- ЛОГИКА ПРОВЕРКИ СТАТУСА СДЕЛКИ ---
def update_trade_statuses(current_price):
    for trade in st.session_state.trades:
        if trade['Статус'] == "OPEN":
            # Проверка для LONG
            if trade['Тип'] == "LONG":
                if current_price >= trade['Тейк'] and trade['Тейк'] > 0:
                    trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price <= trade['Стоп'] and trade['Стоп'] > 0:
                    trade['Статус'] = "❌ STOP LOSS"
            # Проверка для SHORT
            elif trade['Тип'] == "SHORT":
                if current_price <= trade['Тейк'] and trade['Тейк'] > 0:
                    trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price >= trade['Стоп'] and trade['Стоп'] > 0:
                    trade['Статус'] = "❌ STOP LOSS"

if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()
else:
    # --- ЛЕВАЯ ПАНЕЛЬ ---
    with st.sidebar:
        st.header(f"👤 {st.session_state.user}")
        st.subheader("➕ Новая сделка")
        t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        t_coin = st.text_input("Монета", "BTC").upper()
        
        # Получаем текущую цену для удобства ввода
        temp_df = get_crypto_data(t_coin, "5m")
        curr_p = temp_df['close'].iloc[-1] if temp_df is not None else 0.0
        
        t_entry = st.number_input("Вход", value=float(curr_p), format="%.2f")
        t_stop = st.number_input("Стоп", value=0.0, format="%.2f")
        t_take = st.number_input("Тейк", value=0.0, format="%.2f")
        
        if st.button("Открыть позицию", use_container_width=True):
            st.session_state.trades.append({
                "Время": datetime.now().strftime("%H:%M:%S"),
                "Тип": t_side, "Монета": t_coin, "Вход": t_entry, 
                "Стоп": t_stop, "Тейк": t_take, "Статус": "OPEN"
            })
            st.success("Сделка открыта!")
        
        st.divider()
        if st.button("Выход", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- ОСНОВНОЙ ЭКРАН ---
    tab1, tab2 = st.tabs(["🕯 График", "📑 Журнал сделок"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        active_coin = c1.text_input("Тикер", "BTC").upper()
        active_tf = c2.select_slider("Таймфрейм", options=["5m", "15m", "1h", "4h", "1d"], value="15m")
        
        df = get_crypto_data(active_coin, active_tf)
        if df is not None:
            price = df['close'].iloc[-1]
            st.metric(f"Цена {active_coin}/USDT", f"${price:,.2f}")
            
            # ОБНОВЛЯЕМ СТАТУСЫ СДЕЛКИ
            update_trade_statuses(price)
            
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("Обновить"):
                st.rerun()

    with tab2:
        st.subheader("Журнал ордеров")
        if st.session_state.trades:
            df_trades = pd.DataFrame(st.session_state.trades)
            st.dataframe(df_trades.iloc[::-1], use_container_width=True)
        else:
            st.info("Сделок нет")
