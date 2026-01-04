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

# Сброс полей
def reset_order_fields():
    st.session_state["stop_input"] = None
    st.session_state["take_input"] = None
    st.session_state["amount_input"] = 0.0

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
    with st.sidebar:
        st.header(f"👤 {st.session_state.user}")
        st.session_state.deposit = st.number_input("Ваш Депозит ($)", value=float(st.session_state.deposit), format="%.2f")
        
        st.divider()
        st.subheader("➕ Новая сделка")
        
        t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        t_coin = st.text_input("Монета", "BTC").upper()
        
        temp_df = get_crypto_data(t_coin, "5m")
        curr_p = temp_df['close'].iloc[-1] if temp_df is not None else 0.0
        
        t_entry = st.number_input("Цена входа", value=float(curr_p), format="%.2f")
        
        # НОВАЯ ГРАФА: Количество монет
        t_amount = st.number_input("Кол-во монет", value=0.0, step=0.001, format="%.4f", key="amount_input")
        
        # Расчет объема позиции
        position_size = t_entry * t_amount
        if position_size > 0:
            st.caption(f"💰 Объем сделки: {position_size:.2f} $")
            
        t_stop = st.number_input("Уровень СТОП", value=None, placeholder="0.00", format="%.2f", key="stop_input")
        t_take = st.number_input("Уровень ТЕЙК", value=None, placeholder="0.00", format="%.2f", key="take_input")
        
        # Расчет RR
        rr_value = 0.0
        if t_entry and t_stop and t_take:
            try:
                risk = abs(t_entry - t_stop)
                reward = abs(t_take - t_entry)
                if risk > 0:
                    rr_value = reward / risk
                    st.info(f"📊 RR: 1 к {rr_value:.2f}")
            except:
                pass
        
        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if t_stop and t_take and t_amount > 0:
                st.session_state.trades.append({
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": t_side, "Монета": t_coin, "Кол-во": t_amount,
                    "Вход": t_entry, "Стоп": t_stop, "Тейк": t_take, 
                    "RR": round(rr_value, 2), "Статус": "OPEN"
                })
                reset_order_fields()
                st.success("Ордер добавлен!")
                st.rerun()
            else:
                st.error("Заполните Кол-во, Стоп и Тейк!")
        
        st.divider()
        if st.button("Выход", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

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
            
            if st.button("Обновить данные"):
                st.rerun()

    with tab2:
        if st.session_state.trades:
            # Отображаем таблицу с количеством монет
            st.dataframe(pd.DataFrame(st.session_state.trades).iloc[::-1], use_container_width=True)
            if st.button("Очистить журнал"):
                st.session_state.trades = []
                st.rerun()
        else:
            st.info("Журнал пуст")
