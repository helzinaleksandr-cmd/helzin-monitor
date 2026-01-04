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
if 'tf' not in st.session_state: st.session_state.tf = "15m"

# Универсальная функция получения цены для любой монеты
def get_last_price(symbol):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&e=Binance"
    try:
        res = requests.get(url, timeout=2).json()
        return float(res.get('USDT', 0))
    except: return 0.0

def get_ohlc_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    try:
        data = requests.get(url, timeout=5).json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df, float(df['close'].iloc[-1])
    except: pass
    return None, 0.0

# --- ДВИЖОК БЕЗ МИГАНИЯ ---
@st.fragment(run_every=5)
def live_engine(active_ticker):
    # Получаем данные для основного графика
    df, main_price = get_ohlc_data(active_ticker, st.session_state.tf)

    # ПРОВЕРКА ВСЕХ СДЕЛОК (каждая по своей цене)
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            # Берем актуальную цену именно для этой монеты (BTC или ETH)
            trade_price = get_last_price(trade["coin"])
            if trade_price == 0: continue # Пропускаем если ошибка связи

            # Расчет PNL
            if trade["side"] == "LONG":
                pnl_now = (trade_price - trade["entry"]) * trade["qty"]
            else:
                pnl_now = (trade["entry"] - trade_price) * trade["qty"]

            # Проверка закрытия
            is_closed = False
            if trade["side"] == "LONG":
                if trade_price >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif trade_price <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            else:
                if trade_price <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif trade_price >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            
            if is_closed:
                trade["final_pnl"] = pnl_now
            else:
                trade["current_pnl"] = pnl_now # Временное хранение для отображения

    # ОТРИСОВКА
    tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])
    
    with tab_trade:
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric(f"Цена {active_ticker}", f"${main_price:,.2f}")
        c_m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
        c_m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tab_journal:
        if st.session_state.trades:
            h = st.columns([1, 0.8, 0.7, 0.7, 1, 1, 1, 0.6, 1.2, 1, 0.5])
            cols_names = ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "Прибыль ($)", "Статус", ""]
            for col, n in zip(h, cols_names): col.markdown(f"**{n}**")

            for i, t in enumerate(st.session_state.trades):
                # Фиксированная или живая прибыль
                pnl_to_show = t.get("final_pnl") if t.get("final_pnl") is not None else t.get("current_pnl", 0.0)
                
                cols = st.columns([1, 0.8, 0.7, 0.7, 1, 1, 1, 0.6, 1.2, 1, 0.5])
                cols[0].write(t["time"])
                cols[1].write(t["coin"])
                cols[2].write(t["side"])
                cols[3].write(f"{t['qty']}")
                cols[4].write(f"{t['entry']:.2f}")
                cols[5].write(f"{t['sl']:.2f}")
                cols[6].write(f"{t['tp']:.2f}")
                cols[7].write(f"{t['rr']}")
                color = "🟢" if pnl_to_show >= 0 else "🔴"
                cols[8].write(f"{color} ${pnl_to_show:.2f}")
                cols[9].write(t["status"])
                if cols[10].button("🗑️", key=f"del_{i}"):
                    st.session_state.trades.pop(i); st.rerun()

# --- САЙДБАР (Стабильный ввод) ---
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin_input = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=None, placeholder="Цена...", format="%.2f")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...", step=0.0001)
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...", format="%.2f")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...", format="%.2f")
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - sl) if sl else 1
                reward = abs(tp - entry) if tp else 0
                st.session_state.trades.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin_input, "side": side, "entry": float(entry), "qty": float(qty),
                    "sl": float(sl) if sl else 0.0, "tp": float(tp) if tp else 0.0,
                    "rr": round(reward/risk, 2), "status": "В процессе ⏳", "final_pnl": None
                })
                st.rerun()

# --- ВЕРХНЯЯ ПАНЕЛЬ ---
c1, c2, c3 = st.columns([1, 1, 2.5])
with c1: active_symbol = st.text_input("Тикер на графике", value="BTC").upper()
with c2: st.selectbox("Рынок", ["FUTURES", "SPOT"])
with c3:
    st.write("Таймфрейм")
    t_cols = st.columns(5)
    for idx, tf_v in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if t_cols[idx].button(tf_v, key=f"tf_{tf_v}", type="primary" if st.session_state.tf == tf_v else "secondary"):
            st.session_state.tf = tf_v; st.rerun()

# ЗАПУСК
live_engine(active_symbol)
