import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# 1. Настройка терминала
st.set_page_config(page_title="Helzin Futures Terminal", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"

# 2. Умная функция загрузки данных специально для ФЬЮЧЕРСОВ
def get_futures_data(ticker, tf):
    tf_map = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    # Пытаемся сначала найти фьючерсный контракт USDT
    search_tickers = [ticker, f"{ticker}USDT", f"{ticker}USDT_PERP"]
    
    for symbol in search_tickers:
        try:
            suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
            # Принудительно запрашиваем BinanceFutures
            url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=250&aggregate={tf_map.get(tf, 15)}&e=BinanceFutures"
            res = requests.get(url, timeout=5).json()
            
            if res.get('Response') == 'Success' and len(res['Data']['Data']) > 0:
                df = pd.DataFrame(res['Data']['Data'])
                if df['close'].sum() > 0:
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    st.session_state.last_price = float(df['close'].iloc[-1])
                    return df
        except: continue
    return None

# 3. Сайдбар управления
with st.sidebar:
    st.title("👨‍💻 Admin")
    st.session_state.deposit = st.number_input("Баланс USDT", value=float(st.session_state.deposit))
    st.divider()
    
    st.subheader("🚀 Открыть позицию")
    with st.form("futures_trade"):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", value="BTC").upper()
        # Автоподстановка текущей цены фьючерса
        entry = st.number_input("Цена входа", value=float(st.session_state.last_price), format="%.2f")
        amt = st.text_input("Объем (в монетах)")
        sl = st.text_input("Стоп-лосс")
        tp = st.text_input("Тейк-профит")
        
        if st.form_submit_button("ВЫСТАВИТЬ ОРДЕР", use_container_width=True):
            try:
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(),
                    "Время": datetime.now().strftime("%H:%M"),
                    "Тип": side, "Монета": coin, "Вход": entry, 
                    "Кол-во": float(amt), "Stop": float(sl), "Тейк": float(tp),
                    "Статус": "OPEN"
                })
                st.success("Ордер принят!")
                st.rerun()
            except: st.error("Проверьте числа (используйте точку)")

# 4. Основной экран
# Метрики в ряд
c1, c2, c3 = st.columns(3)
c1.metric("Текущий фьючерс", f"${st.session_state.last_price:,.2f}")
c2.metric("Свободный маржа", f"${st.session_state.deposit:,.2f}")
c3.metric("Позиций в рынке", len([t for t in st.session_state.trades if t['Status'] == "OPEN" if 'Status' in t else 1]))

# Выбор тикера и таймфрейма
t_col, tf_col = st.columns([1, 2])
active_ticker = t_col.text_input("Торговая пара", "BTC").upper()

with tf_col:
    st.write("Период")
    t_btns = st.columns(5)
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if t_btns[i].button(f, key=f, type="primary" if st.session_state.timeframe == f else "secondary"):
            st.session_state.timeframe = f; st.rerun()

# Загрузка и отрисовка
df = get_futures_data(active_ticker, st.session_state.timeframe)

if df is not None:
    fig = go.Figure(data=[go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00ff88', decreasing_line_color='#ff4b4b'
    )])
    
    # Линии твоих сделок на графике
    for tr in st.session_state.trades:
        if tr['Статус'] == "OPEN" and tr['Монета'] == active_ticker:
            fig.add_hline(y=tr['Вход'], line_color="white", annotation_text="ВХОД")
            fig.add_hline(y=tr['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
            fig.add_hline(y=tr['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

    fig.update_layout(
        template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(side="right", autorange=True, gridcolor='rgba(255,255,255,0.05)')
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"❌ Не удалось подключиться к Binance Futures для {active_ticker}. Проверьте интернет или тикер.")

# Журнал под графиком
st.subheader("📝 Текущие позиции")
if not st.session_state.trades:
    st.info("Активных позиций нет")
else:
    for t in reversed(st.session_state.trades):
        cols = st.columns([1, 1, 1, 1, 1, 0.5])
        cols[0].write(t['Время'])
        cols[1].write(f"**{t['Монета']} {t['Тип']}**")
        cols[2].write(f"Вход: {t['Вход']}")
        cols[3].write(f"Кол-во: {t['Кол-во']}")
        cols[4].write(f"🟢 {t['Тейк']} / 🔴 {t['Stop']}")
        if cols[5].button("✖", key=t['id']):
            st.session_state.trades.remove(t); st.rerun()
