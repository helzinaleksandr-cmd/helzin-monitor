import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация состояния
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"

def get_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            st.session_state.price = float(df['close'].iloc[-1])
            return df
    except: return None
    return None

# --- ГЛАВНЫЙ ДВИЖОК БЕЗ ПЕРЕЗАГРУЗКИ ---
@st.fragment(run_every=5) # Обновляет только эту часть каждые 5 секунд БЕЗ МИГАНИЯ
def live_engine(ticker):
    df = get_data(ticker, st.session_state.tf)
    cur_p = st.session_state.price

    # 1. Проверка условий сделок (фоновая)
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            pnl_now = (cur_p - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - cur_p) * trade["qty"]
            is_closed = False
            if trade["side"] == "LONG":
                if cur_p >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif cur_p <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            else:
                if cur_p <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif cur_p >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            if is_closed: trade["final_pnl"] = pnl_now

    # 2. Отрисовка интерфейса внутри фрагмента
    tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])
    
    with tab_trade:
        m1, m2, m3 = st.columns(3)
        m1.metric("Текущая цена", f"${cur_p:,.2f}")
        m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
        m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tab_journal:
        if st.session_state.trades:
            h = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
            for col, n in zip(h, ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "Прибыль ($)", "Статус", ""]):
                col.markdown(f"**{n}**")
            for i, trade in enumerate(st.session_state.trades):
                pnl = trade["final_pnl"] if trade["final_pnl"] is not None else (
                    (cur_p - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - cur_p) * trade["qty"]
                )
                cols = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
                cols[0].write(trade["time"])
                cols[1].write(trade["coin"])
                cols[2].write(trade["side"])
                cols[3].write(f"{trade['qty']}")
                cols[4].write(f"{trade['entry']:.2f}")
                cols[5].write(f"{trade['sl']:.2f}")
                cols[6].write(f"{trade['tp']:.2f}")
                cols[7].write(f"{trade['rr']}")
                cols[8].write(f"{'🟢' if pnl >= 0 else '🔴'} ${pnl:.2f}")
                cols[9].write(trade["status"])
                if cols[10].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades.pop(i); st.rerun()

# --- САЙДБАР (Вне фрагмента, всегда стабилен) ---
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # Пустые поля
        entry = st.number_input("Цена входа", value=None, placeholder="Цена...", format="%.2f")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...", step=0.0001)
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...", format="%.2f")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...", format="%.2f")
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - sl) if sl else 0
                reward = abs(tp - entry) if tp else 0
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin, "side": side, "entry": float(entry), "qty": float(qty),
                    "sl": float(sl) if sl else 0.0, "tp": float(tp) if tp else 0.0,
                    "rr": round(reward/risk, 2) if risk > 0 else 0.0, "status": "В процессе ⏳", "final_pnl": None
                })
                st.rerun()

# --- ВЕРХНЯЯ ПАНЕЛЬ ТАЙМФРЕЙМОВ ---
c1, c2, c3 = st.columns([1, 1, 2.5])
with c1: active_ticker = st.text_input("Тикер", value="BTC").upper()
with c2: st.selectbox("Рынок", ["FUTURES", "SPOT"])
with c3:
    st.write("Таймфрейм")
    tf_cols = st.columns(5)
    for idx, tf_item in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if tf_cols[idx].button(tf_item, key=f"tf_{tf_item}", type="primary" if st.session_state.tf == tf_item else "secondary"):
            st.session_state.tf = tf_item; st.rerun()

# ЗАПУСК ДВИЖКА
live_engine(active_ticker)
