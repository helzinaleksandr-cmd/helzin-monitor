import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# 1. Настройка страницы
st.set_page_config(page_title="Helzin Terminal", layout="wide")

# 2. Инициализация и загрузка данных
DB_FILE = "trades_history.json"

if 'trades' not in st.session_state:
    st.session_state.trades = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.trades = data.get("trades", [])
        except: pass

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

# 3. Получение данных
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

# 4. Интерфейс
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    if st.button("Войти в систему"): 
        st.session_state.logged_in = True
        st.rerun()
else:
    with st.sidebar:
        st.header("👤 admin")
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        st.subheader("➕ Новая сделка")
        
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin_in = st.text_input("Монета", value="BTC", key="side_coin", help="Введите тикер").upper()
        
        # Авто-подстановка текущей цены
        c_pr = st.session_state.last_price
        ent = st.text_input("Вход", value=str(c_pr) if c_pr > 0 else "")
        amt = st.text_input("Кол-во")
        sl = st.text_input("Стоп")
        tp = st.text_input("Тейк")
        
        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            try:
                # Очистка и конвертация ввода
                vals = [x.replace(',','.').strip() for x in [ent, amt, sl, tp]]
                e, a, s, tk = [float(x) for x in vals]
                
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": side, "Монета": coin_in, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk,
                    "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                })
                save_data(); st.rerun()
            except: st.error("❌ Ошибка: Вводите только числа")
        
        if st.button("Выход"): 
            st.session_state.logged_in = False
            st.rerun()

    t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    
    with t1:
        c1, c2, c3 = st.columns([1, 1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_coin").upper()
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
        
        with c3:
            st.write("Таймфрейм")
            cols = st.columns(5)
            for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if cols[i].button(f, key=f"tf_{f}", type="primary" if st.session_state.timeframe == f else "secondary"):
                    st.session_state.timeframe = f; st.rerun()

        df = get_crypto_data(active_coin, st.session_state.timeframe, m_type)
        if df is not None:
            # Метрики
            closed = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
            total_pnl = sum([(t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num']) for t in closed])
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Цена", f"${st.session_state.last_price:,.2f}")
            m2.metric("P/L", f"${total_pnl:,.2f}")
            m3.metric("Активных", len([t for t in st.session_state.trades if t['Статус'] == "OPEN"]))

            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            
            for tr in st.session_state.trades:
                if tr['Статус'] == "OPEN" and tr['Монета'] == active_coin:
                    fig.add_hline(y=tr['Вход'], line_color="white", annotation_text="Вход")
                    fig.add_hline(y=tr['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                    fig.add_hline(y=tr['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10),
                              yaxis=dict(side="right", fixedrange=False, autorange=True), xaxis=dict(fixedrange=False))
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    with t2:
        if not st.session_state.trades: st.write("Нет сделок")
        else:
            st.subheader("Список всех сделок")
            for i, tr in enumerate(reversed(st.session_state.trades)):
                c = st.columns([2, 1, 1, 1, 1])
                c[0].write(f"**{tr['Монета']}** ({tr['Тип']}) — {tr['Время']}")
                c[1].write(f"Вход: {tr['Вход']}")
                c[2].write(f"Статус: {tr['Статус']}")
                if c[4].button("🗑️", key=f"del_{i}"):
                    st.session_state.trades.remove(tr); save_data(); st.rerun()
            
            st.divider()
            if st.button("🔥 ОЧИСТИТЬ ВСЮ ИСТОРИЮ", use_container_width=True):
                st.session_state.trades = []
                save_data(); st.rerun()
