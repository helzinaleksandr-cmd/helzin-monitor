import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# 1. Настройка страницы
st.set_page_config(page_title="Helzin Terminal Ultimate", layout="wide")

# 2. Инициализация состояния
if 'trades' not in st.session_state: st.session_state.trades = []
if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC"

DB_FILE = "trades_history.json"

def save_data():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"trades": st.session_state.trades, "deposit": st.session_state.deposit}, f)
    except: pass

# 3. Функция загрузки с исправлением "дыр" в данных
def get_clean_data(ticker, tf, market):
    tf_map = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    exchange = "Binance" if market == "SPOT" else "BinanceFutures"
    
    try:
        # Пытаемся получить минутные или часовые данные
        suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
        url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={ticker}&tsym=USDT&limit=300&aggregate={tf_map.get(tf, 15)}&e={exchange}"
        
        res = requests.get(url, timeout=5).json()
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            # Исправляем визуальные разрывы: заполняем пустые значения предыдущими
            df = df.replace(0, pd.NA).ffill()
            df['time'] = pd.to_datetime(df['time'], unit='s')
            st.session_state.last_price = float(df['close'].iloc[-1])
            return df
    except:
        return None
    return None

# 4. Сайдбар
with st.sidebar:
    st.header("👤 admin")
    st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
    st.divider()
    
    st.subheader("➕ Новая сделка")
    with st.form("trade_input"):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", value=st.session_state.active_coin).upper()
        # ПОЛЕ ВХОДА ТЕПЕРЬ ВСЕГДА СВЕЖЕЕ
        entry = st.text_input("Цена входа", value=str(round(st.session_state.last_price, 2)))
        amount = st.text_input("Кол-во монет")
        stop = st.text_input("Стоп-лосс")
        take = st.text_input("Тейк-профит")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            try:
                e, a, s, t = [float(x.replace(',','.')) for x in [entry, amount, stop, take]]
                st.session_state.trades.append({
                    "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                    "Тип": side, "Монета": coin, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": t, "Статус": "OPEN"
                })
                save_data(); st.rerun()
            except: st.error("Ошибка в данных")

# 5. Основная панель
t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])

with t1:
    c1, c2, c3 = st.columns([1, 1, 3])
    st.session_state.active_coin = c1.text_input("Тикер", value=st.session_state.active_coin, key="k1").upper()
    m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"], key="k2")
    
    with c3:
        st.write("Таймфрейм")
        ts = st.columns(5)
        for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
            if ts[i].button(f, key=f"tf_{f}", type="primary" if st.session_state.timeframe == f else "secondary"):
                st.session_state.timeframe = f; st.rerun()

    df = get_clean_data(st.session_state.active_coin, st.session_state.timeframe, m_type)

    # Верхние карточки
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Текущая цена", f"${st.session_state.last_price:,.2f}")
    m_col2.metric("P/L", "$0.00")
    m_col3.metric("Сделок", len([t for t in st.session_state.trades if t['Статус'] == "OPEN"]))

    if df is not None:
        # Создаем плотный график без разрывов
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00ff88', decreasing_line_color='#ff4b4b'
        )])
        
        # Рисуем линии только для активной монеты
        for tr in st.session_state.trades:
            if tr['Статус'] == "OPEN" and tr['Монета'] == st.session_state.active_coin:
                fig.add_hline(y=tr['Вход'], line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=tr['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                fig.add_hline(y=tr['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

        fig.update_layout(
            template="plotly_dark", height=650, margin=dict(l=0, r=0, t=0, b=0),
            xaxis_rangeslider_visible=False,
            yaxis=dict(side="right", autorange=True, fixedrange=False, gridcolor='rgba(255,255,255,0.1)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Ожидание данных... Попробуйте переключить таймфрейм.")

with t2:
    if not st.session_state.trades: st.write("Журнал пуст")
    else:
        for tr in reversed(st.session_state.trades):
            col = st.columns([1, 1, 1, 1, 1, 0.5])
            col[0].write(tr['Время'])
            col[1].write(tr['Монета'])
            col[2].write(f"${tr['Вход']}")
            col[3].write(str(tr['Кол-во']))
            col[4].write(tr['Статус'])
            if col[5].button("🗑️", key=f"del_{tr['id']}"):
                st.session_state.trades.remove(tr); save_data(); st.rerun()
