import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

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

def check_trade_logic(trades, current_price):
    for trade in trades:
        if trade['Статус'] == "OPEN":
            if trade['Тип'] == "LONG":
                if current_price >= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price <= trade['Стоп']: trade['Статус'] = "❌ STOP LOSS"
            else:
                if current_price <= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price >= trade['Стоп']: trade['Статус'] = "❌ STOP LOSS"

@st.fragment(run_every=3)
def live_chart_section(coin, tf):
    df = get_crypto_data(coin, tf)
    if df is not None:
        price_now = df['close'].iloc[-1]
        st.metric(f"{coin}/USDT (LIVE)", f"${price_now:,.2f}")
        check_trade_logic(st.session_state.trades, price_now)
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

# БЛОК ВХОДА
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    with st.form("login_form"):
        u = st.text_input("Логин")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if u == "admin" and p == "12345":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Ошибка входа")
else:
    with st.sidebar:
        st.header(f"👤 admin")
        st.session_state.deposit = st.number_input("Ваш Депозит ($)", value=float(st.session_state.deposit), format="%.2f")
        st.divider()
        st.subheader("➕ Новая сделка")
        
        # Используем форму с АВТО-ОЧИСТКОЙ ПОЛЕЙ
        with st.form("trade_form", clear_on_submit=True):
            t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
            t_coin = st.text_input("Монета", value="BTC").upper()
            
            # Поля пустые по умолчанию
            t_entry = st.number_input("Цена входа", value=None, placeholder="0.00", format="%.2f")
            t_amount = st.number_input("Кол-во монет", value=None, placeholder="0.00", format="%.4f")
            t_stop = st.number_input("Уровень СТОП", value=None, placeholder="0.00", format="%.2f")
            t_take = st.number_input("Уровень ТЕЙК", value=None, placeholder="0.00", format="%.2f")
            
            submit_trade = st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True)
            
            if submit_trade:
                if t_entry and t_stop and t_take and t_amount:
                    risk = abs(t_entry - t_stop)
                    reward = abs(t_take - t_entry)
                    rr_val = round(reward / risk, 2) if risk > 0 else 0
                    p_res = f"+{reward * t_amount:.2f} / -{risk * t_amount:.2f}"
                    
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(),
                        "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": t_side, "Монета": t_coin, "Кол-во": t_amount,
                        "Вход": t_entry, "Стоп": t_stop, "Тейк": t_take, 
                        "RR": rr_val, "PL": p_res, "Статус": "OPEN"
                    })
                    st.rerun()
                else:
                    st.error("Заполни все поля!")
        
        if st.button("Выйти"):
            st.session_state.logged_in = False
            st.rerun()

    tab1, tab2 = st.tabs(["🕯 Торговый график", "📑 Журнал сделок"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_coin").upper()
        active_tf = c2.select_slider("Таймфрейм", options=["5m", "15m", "1h", "4h", "1d"], value="15m")
        live_chart_section(active_coin, active_tf)

    with tab2:
        if not st.session_state.trades:
            st.info("Журнал пуст")
        else:
            cols = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
            headers = ["Время", "Тип", "Монета", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "P/L ($)", "Статус", "Del"]
            for col, h in zip(cols, headers): col.write(f"**{h}**")
            
            for trade in reversed(st.session_state.trades):
                c = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
                c[0].write(trade["Время"])
                c[1].write(trade["Тип"])
                c[2].write(trade["Монета"])
                c[3].write(str(trade["Кол-во"]))
                c[4].write(str(trade["Вход"]))
                c[5].write(str(trade["Стоп"]))
                c[6].write(str(trade["Тейк"]))
                c[7].write(str(trade["RR"]))
                c[8].write(trade["PL"])
                color = "green" if "TAKE" in trade["Статус"] else "red" if "STOP" in trade["Статус"] else "white"
                c[9].markdown(f":{color}[{trade['Статус']}]")
                if c[10].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades = [t for t in st.session_state.trades if t['id'] != trade['id']]
                    st.rerun()
