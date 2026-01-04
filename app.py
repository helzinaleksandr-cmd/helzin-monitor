import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Настройки страницы
st.set_page_config(page_title="Helzin Terminal", layout="wide")

# 2. Инициализация памяти (Session State)
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'trades' not in st.session_state: st.session_state.trades = []
if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"
if 'equity_style' not in st.session_state: st.session_state.equity_style = "#00ff88"

# 3. Функции логики
def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=1000&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except: return None

def check_trade_logic(price):
    changed = False
    for t in st.session_state.trades:
        if t['Статус'] == "OPEN":
            if t['Тип'] == "LONG":
                if price >= t['Тейк']: t['Статус'], changed = "✅ TAKE PROFIT", True
                elif price <= t['Stop']: t['Статус'], changed = "❌ STOP LOSS", True
            else:
                if price <= t['Тейк']: t['Статус'], changed = "✅ TAKE PROFIT", True
                elif price >= t['Stop']: t['Статус'], changed = "❌ STOP LOSS", True
    return changed

# 4. График с МАСШТАБОМ
@st.fragment(run_every=3)
def live_chart_section(coin, tf, market_type):
    df = get_crypto_data(coin, tf, market_type)
    if df is not None:
        price_now = df['close'].iloc[-1]
        st.metric(f"{coin}/USDT", f"${price_now:,.2f}")
        if check_trade_logic(price_now): st.rerun()
            
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        for t in st.session_state.trades:
            if t['Статус'] == "OPEN" and t['Монета'] == coin:
                fig.add_hline(y=t['Вход'], line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=t['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                fig.add_hline(y=t['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
                          margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(side="right", fixedrange=False))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# 5. Интерфейс (Вход)
if not st.session_state.logged_in:
    with st.form("login"):
        u, p = st.text_input("Логин"), st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти") and u == "admin" and p == "12345":
            st.session_state.logged_in = True
            st.rerun()
else:
    # Сайдбар
    with st.sidebar:
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        with st.form("trade", clear_on_submit=True):
            side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
            coin = st.text_input("Монета", "BTC").upper()
            en, am, sl, tp = st.text_input("Вход"), st.text_input("Кол-во"), st.text_input("Стоп"), st.text_input("Тейк")
            if st.form_submit_button("ОТКРЫТЬ"):
                try:
                    e, a, s, t = float(en), float(am), float(sl), float(tp)
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M"),
                        "Тип": side, "Монета": coin, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": t,
                        "profit_num": abs(t-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                    })
                    st.rerun()
                except: st.error("Ошибка в числах")

    # Основной экран
    tab1, tab2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    with tab1:
        c1, c2, c3 = st.columns([1, 1, 3]) # Сначала создаем колонки!
        active_coin = c1.text_input("Тикер", "BTC").upper()
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
        with c3: # Теперь c3 существует и ошибки не будет
            st.write("Таймфрейм")
            cols = st.columns(5)
            tfs = ["5m", "15m", "1h", "4h", "1d"]
            for i, f in enumerate(tfs):
                if cols[i].button(f, use_container_width=True):
                    st.session_state.timeframe = f
                    st.rerun()
        live_chart_section(active_coin, st.session_state.timeframe, m_type)

    with tab2:
        st.write(pd.DataFrame(st.session_state.trades) if st.session_state.trades else "Пусто")
