import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация данных
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

def update_trade_statuses(current_price):
    for trade in st.session_state.trades:
        if trade['Статус'] == "OPEN":
            if trade['Тип'] == "LONG":
                if trade['Тейк'] and current_price >= trade['Тейк']:
                    trade['Статус'] = "✅ TAKE PROFIT"
                elif trade['Стоп'] and current_price <= trade['Стоп']:
                    trade['Статус'] = "❌ STOP LOSS"
            elif trade['Тип'] == "SHORT":
                if trade['Тейк'] and current_price <= trade['Тейк']:
                    trade['Статус'] = "✅ TAKE PROFIT"
                elif trade['Стоп'] and current_price >= trade['Стоп']:
                    trade['Статус'] = "❌ STOP LOSS"

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
        
        # ПОЛЕ КОЛ-ВО ТЕПЕРЬ ПУСТОЕ
        t_amount = st.number_input("Кол-во монет", value=None, placeholder="Введите кол-во...", format="%.4f", key="amount_input")
        
        # Расчет объема
        if t_amount and t_entry:
            st.caption(f"💰 Объем: {t_entry * t_amount:.2f} $")
            
        t_stop = st.number_input("Уровень СТОП", value=None, placeholder="0.00", format="%.2f", key="stop_input")
        t_take = st.number_input("Уровень ТЕЙК", value=None, placeholder="0.00", format="%.2f", key="take_input")
        
        # ПРАВИЛЬНЫЙ РАСЧЕТ RR
        rr_value = 0.0
        if t_entry and t_stop and t_take:
            try:
                if t_side == "LONG":
                    risk = t_entry - t_stop
                    reward = t_take - t_entry
                else:
                    risk = t_stop - t_entry
                    reward = t_entry - t_take
                
                if risk > 0:
                    rr_value = reward / risk
                    color = "green" if rr_value >= 2 else "red"
                    st.markdown(f"📊 **RR: 1 к {rr_value:.2f}**")
            except:
                pass
        
        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if t_stop and t_take and t_amount:
                st.session_state.trades.append({
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": t_side, "Монета": t_coin, "Кол-во": t_amount,
                    "Вход": t_entry, "Стоп": t_stop, "Тейк": t_take, 
                    "RR": round(rr_value, 2), "Статус": "OPEN"
                })
                st.success("Сделка открыта!")
                st.rerun() # Автоматически очистит поля за счет rerun и пустых дефолтов
            else:
                st.error("Заполните все поля!")

    tab1, tab2 = st.tabs(["🕯 График", "📑 Журнал"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_ticker").upper()
        active_tf = c2.select_slider("Таймфрейм", options=["5m", "15m", "1h", "4h", "1d"], value="15m")
        
        df = get_crypto_data(active_coin, active_tf)
        if df is not None:
            price = df['close'].iloc[-1]
            st.metric(f"{active_coin}/USDT", f"${price:,.2f}", delta=f"Депо: {st.session_state.deposit}$")
            update_trade_statuses(price)
            
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            )])
            fig.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
    with tab2:
        if st.session_state.trades:
            st.dataframe(pd.DataFrame(st.session_state.trades).iloc[::-1], use_container_width=True)
            if st.button("Очистить журнал"):
                st.session_state.trades = []
                st.rerun()
