import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Ultimate", layout="wide")

# Инициализация состояния
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance_init' not in st.session_state: st.session_state.balance_init = 1000.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"

# Функция получения цены
def get_last_price(symbol):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&e=Binance"
    try:
        res = requests.get(url, timeout=2).json()
        return float(res.get('USDT', 0))
    except: return 0.0

# Функция данных для графика
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

# --- ГЛАВНЫЙ ДВИЖОК ОБНОВЛЕНИЯ ---
@st.fragment(run_every=5)
def live_engine(active_ticker):
    df, main_price = get_ohlc_data(active_ticker, st.session_state.tf)
    
    # 1. Фоновый расчет и авто-закрытие
    total_pnl = 0.0
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            t_price = get_last_price(trade["coin"])
            if t_price == 0: continue
            
            pnl = (t_price - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - t_price) * trade["qty"]
            
            # Проверка авто-закрытия
            closed = False
            if trade["side"] == "LONG":
                if t_price >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; closed = True
                elif t_price <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; closed = True
            else:
                if t_price <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; closed = True
                elif t_price >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; closed = True
            
            if closed: trade["final_pnl"] = pnl
            else: trade["current_pnl"] = pnl
        
        # Считаем общий профит для статистики
        total_pnl += trade.get("final_pnl", 0) if trade.get("final_pnl") is not None else trade.get("current_pnl", 0)

    # 2. Отрисовка вкладок
    t1, t2 = st.tabs(["🕯 Торговля", "📓 Журнал и Аналитика"])

    with t1:
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {active_ticker}", f"${main_price:,.2f}")
        m2.metric("Баланс + PNL", f"${(st.session_state.balance_init + total_pnl):,.2f}")
        m3.metric("Активных сделок", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            # ВОЗВРАЩАЕМ ПУНКТИРНУЮ ЛИНИЮ ЦЕНЫ
            fig.add_hline(y=main_price, line_dash="dash", line_color="yellow", annotation_text=f" Сейчас: {main_price}")
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        # Секция аналитики
        st.subheader("📊 Кривая доходности")
        closed_trades = [t for t in st.session_state.trades if t.get("final_pnl") is not None]
        if closed_trades:
            equity = [st.session_state.balance_init]
            for t in closed_trades: equity.append(equity[-1] + t["final_pnl"])
            fig_equity = go.Figure(data=go.Scatter(y=equity, mode='lines+markers', line=dict(color='#00ff00')))
            fig_equity.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_equity, use_container_width=True)

        # Журнал сделок
        st.subheader("📝 Список сделок")
        if st.session_state.trades:
            h = st.columns([1, 0.8, 0.7, 0.7, 1, 1, 1, 1, 1, 0.6])
            for col, n in zip(h, ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп/Тейк", "Прибыль", "Статус", "Закрыть", ""]):
                col.markdown(f"**{n}**")
            
            for i, t in enumerate(st.session_state.trades):
                p_show = t.get("final_pnl") if t.get("final_pnl") is not None else t.get("current_pnl", 0)
                cols = st.columns([1, 0.8, 0.7, 0.7, 1, 1, 1, 1, 1, 0.6])
                cols[0].write(t["time"])
                cols[1].write(t["coin"])
                cols[2].write(t["side"])
                cols[3].write(f"{t['qty']}")
                cols[4].write(f"{t['entry']:.1f}")
                cols[5].write(f"{t['sl']}/{t['tp']}")
                cols[6].write(f"{'🟢' if p_show >= 0 else '🔴'} ${p_show:.2f}")
                cols[7].write(t["status"])
                
                # КНОПКА РУЧНОГО ЗАКРЫТИЯ
                if "⏳" in t["status"]:
                    if cols[8].button("Фикс 🏁", key=f"fix_{i}"):
                        t["final_pnl"] = p_show
                        t["status"] = "Вручную 🔒"
                        st.rerun()
                else: cols[8].write("—")
                
                if cols[9].button("🗑️", key=f"del_{i}"):
                    st.session_state.trades.pop(i); st.rerun()

# --- САЙДБАР ---
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance_init = st.number_input("Начальный Депозит ($)", value=float(st.session_state.balance_init))
    st.divider()
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin_in = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=None, placeholder="Вход...")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...")
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...")
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                st.session_state.trades.append({
                    "time": datetime.now().strftime("%H:%M"), "coin": coin_in, "side": side, 
                    "entry": float(entry), "qty": float(qty), "sl": float(sl or 0), "tp": float(tp or 0),
                    "status": "В процессе ⏳", "final_pnl": None
                })
                st.rerun()

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
c1, c2, c3 = st.columns([1, 1, 2.5])
with c1: act_ticker = st.text_input("Тикер на графике", value="BTC").upper()
with c2: st.selectbox("Рынок", ["FUTURES", "SPOT"])
with c3:
    st.write("Таймфрейм")
    ts = st.columns(5)
    for idx, v in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if ts[idx].button(v, key=f"tf_{v}", type="primary" if st.session_state.tf == v else "secondary"):
            st.session_state.tf = v; st.rerun()

live_engine(act_ticker)
