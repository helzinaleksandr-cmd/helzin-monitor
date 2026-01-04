import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация состояния
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0
if 'price' not in st.session_state:
    st.session_state.price = 0.0
if 'tf' not in st.session_state:
    st.session_state.tf = "15m"

# Функция получения данных (БЫСТРАЯ — Binance/CryptoCompare)
def get_data(symbol, tf):
    # Маппинг таймфреймов
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            current_price = float(df['close'].iloc[-1])
            st.session_state.price = current_price
            return df, current_price
        return None, 0.0
    except Exception as e:
        return None, 0.0

# === САЙДБАР ===
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))

    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # Поля пустые для удобства
        entry = st.number_input("Цена входа", min_value=0.0, value=float(st.session_state.price), format="%.2f")
        qty = st.number_input("Кол-во монет", min_value=0.0, value=0.0, step=0.001)
        sl = st.number_input("Стоп-лосс", min_value=0.0, value=0.0, format="%.2f")
        tp = st.number_input("Тейк-профит", min_value=0.0, value=0.0, format="%.2f")

        submitted = st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True)
        if submitted and qty > 0 and entry > 0:
            risk = abs(entry - sl) if sl > 0 else 0
            reward = abs(tp - entry) if tp > 0 else 0
            rr = round(reward / risk, 2) if risk > 0 else 0.0

            st.session_state.trades.append({
                "id": time.time(),
                "time": datetime.now().strftime("%H:%M:%S"),
                "coin": coin,
                "side": side,
                "entry": entry,
                "qty": qty,
                "sl": sl,
                "tp": tp,
                "rr": rr,
                "status": "В процессе ⏳"
            })
            st.rerun()

# === ОСНОВНЫЕ ВКЛАДКИ ===
tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    col1, col2 = st.columns([1, 3])
    with col1:
        ticker = st.text_input("Тикер", value="BTC").upper()
        st.write("Таймфрейм")
        tf_cols = st.columns(5)
        tfs = ["5m", "15m", "1h", "4h", "1d"]
        for i, tf_val in enumerate(tfs):
            if tf_cols[i].button(tf_val, key=f"tf_{tf_val}"):
                st.session_state.tf = tf_val
                st.rerun()

    df, current_price = get_data(ticker, st.session_state.tf)

    # Метрики
    m1, m2, m3 = st.columns(3)
    m1.metric("Текущая цена", f"${current_price:,.2f}" if current_price > 0 else "—")
    m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
    m3.metric("Активных сделок", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

    # График
    if df is not None and not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        )])
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Нажми кнопку ниже, чтобы загрузить данные.")
    
    if st.button("🔄 Обновить цену и график", use_container_width=True):
        st.rerun()

# === ЖУРНАЛ ===
with tab_journal:
    st.subheader("📓 Журнал сделок")

    if st.session_state.trades:
        # Сетка таблицы
        headers = st.columns([1, 1, 1, 1, 1, 1, 0.8, 1.2, 1, 0.5])
        header_names = ["Время", "Актив", "Тип", "Вход", "Стоп", "Тейк", "RR", "Прибыль ($)", "Статус", ""]
        for col, name in zip(headers, header_names):
            col.markdown(f"**{name}**")

        for trade in st.session_state.trades:
            # Считаем прибыль на основе ПОСЛЕДНЕЙ полученной цены
            cur_p = st.session_state.price if st.session_state.price > 0 else trade["entry"]

            # PnL (Прибыль)
            if trade["side"] == "LONG":
                pnl = (cur_p - trade["entry"]) * trade["qty"]
            else:
                pnl = (trade["entry"] - cur_p) * trade["qty"]

            # Авто-закрытие
            if "⏳" in trade["status"]:
                if trade["side"] == "LONG":
                    if cur_p >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"
                    elif cur_p <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"
                else: # SHORT
                    if cur_p <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"
                    elif cur_p >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"

            cols = st.columns([1, 1, 1, 1, 1, 1, 0.8, 1.2, 1, 0.5])
            cols[0].write(trade["time"])
            cols[1].write(trade["coin"])
            cols[2].write(trade["side"])
            cols[3].write(f"{trade['entry']:.2f}")
            cols[4].write(f"{trade['sl']:.2f}")
            cols[5].write(f"{trade['tp']:.2f}")
            cols[6].write(f"{trade['rr']}")
            # Цветной вывод прибыли
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            cols[7].write(f"{pnl_color} ${pnl:.2f}")
            cols[8].write(trade["status"])
            if cols[9].button("🗑️", key=f"del_{trade['id']}"):
                st.session_state.trades.remove(trade)
                st.rerun()
    else:
        st.info("Журнал пуст.")
