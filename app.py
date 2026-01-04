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

# Функция получения данных
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
            # Важно: Сразу пишем цену в состояние, чтобы все функции её видели
            st.session_state.price = float(df['close'].iloc[-1])
            return df
    except:
        return None
    return None

# --- АВТОМАТИЧЕСКАЯ ПРОВЕРКА (ГЛАВНЫЙ ДВИЖОК) ---
# Обновляем данные в фоне каждые 5-10 секунд
refresh_sec = 7 
ticker_global = "BTC" # Можно вынести в ввод

# Каждое обновление страницы или таймера проверяем сделки
df_latest = get_data(ticker_global, st.session_state.tf)
cur_p = st.session_state.price

for trade in st.session_state.trades:
    if "⏳" in trade["status"]:
        # Считаем текущий профит для проверки закрытия
        pnl_check = (cur_p - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - cur_p) * trade["qty"]
        
        closed = False
        if trade["side"] == "LONG":
            if cur_p >= trade["tp"] and trade["tp"] > 0:
                trade["status"] = "Тейк ✅"; closed = True
            elif cur_p <= trade["sl"] and trade["sl"] > 0:
                trade["status"] = "Стоп ❌"; closed = True
        else: # SHORT
            if cur_p <= trade["tp"] and trade["tp"] > 0:
                trade["status"] = "Тейк ✅"; closed = True
            elif cur_p >= trade["sl"] and trade["sl"] > 0:
                trade["status"] = "Стоп ❌"; closed = True
        
        if closed:
            trade["final_pnl"] = pnl_check # ФИКСИРУЕМ ПРИБЫЛЬ НА МОМЕНТ ЗАКРЫТИЯ

# --- САЙДБАР ---
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        # ПУСТЫЕ СТРОЧКИ (как ты просил)
        entry = st.number_input("Цена входа", value=None, placeholder="Цена...", format="%.2f")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...", step=0.0001)
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...", format="%.2f")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...", format="%.2f")

        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - sl) if sl else 0
                reward = abs(tp - entry) if tp else 0
                rr = round(reward / risk, 2) if risk > 0 else 0.0
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin, "side": side, "entry": float(entry),
                    "qty": float(qty), "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, "rr": rr, 
                    "status": "В процессе ⏳", "final_pnl": None 
                })
                st.rerun()

# --- ВКЛАДКИ ---
tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1: ticker = st.text_input("Тикер", value="BTC").upper()
    with c2: st.selectbox("Рынок", ["FUTURES", "SPOT"])
    with c3:
        st.write("Таймфрейм")
        tf_list = ["5m", "15m", "1h", "4h", "1d"]
        cols = st.columns(len(tf_list))
        for idx, tf_item in enumerate(tf_list):
            is_active = st.session_state.tf == tf_item
            if cols[idx].button(tf_item, key=f"tf_{tf_item}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state.tf = tf_item; st.rerun()

    m1, m2, m3 = st.columns(3)
    m1.metric("Текущая цена", f"${cur_p:,.2f}" if cur_p > 0 else "—")
    m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
    m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

    if df_latest is not None:
        fig = go.Figure(data=[go.Candlestick(x=df_latest['time'], open=df_latest['open'], high=df_latest['high'], low=df_latest['low'], close=df_latest['close'])])
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab_journal:
    st.subheader("📓 Журнал сделок")
    if st.session_state.trades:
        # ПРАВИЛЬНЫЕ КОЛОНКИ С КОЛ-ВОМ
        h = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
        names = ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "Прибыль ($)", "Статус", ""]
        for col, n in zip(h, names): col.markdown(f"**{n}**")

        for i, trade in enumerate(st.session_state.trades):
            # Показываем или финальную прибыль, или живую
            display_pnl = trade["final_pnl"] if trade["final_pnl"] is not None else (
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
            pnl_color = "🟢" if display_pnl >= 0 else "🔴"
            cols[8].write(f"{pnl_color} ${display_pnl:.2f}")
            cols[9].write(trade["status"])
            if cols[10].button("🗑️", key=f"del_{trade['id']}"):
                st.session_state.trades.pop(i); st.rerun()

# --- ТАЙМЕР ОБНОВЛЕНИЯ ---
time.sleep(refresh_sec)
st.rerun()
