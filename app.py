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
if 'ticker' not in st.session_state: st.session_state.ticker = "BTC"

def get_crypto_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    try:
        response = requests.get(url, timeout=4)
        data = response.json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df, float(df['close'].iloc[-1])
    except:
        return None, 0.0
    return None, 0.0

# Основной цикл обновления (5 секунд)
df_main, current_market_price = get_crypto_data(st.session_state.ticker, st.session_state.tf)
if current_market_price > 0:
    st.session_state.price = current_market_price

# Проверка сделок
for trade in st.session_state.trades:
    if "⏳" in trade["status"]:
        check_p = current_market_price if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
        if check_p > 0:
            is_closed = False
            pnl_final = (check_p - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - check_p) * trade["qty"]
            if trade["side"] == "LONG":
                if check_p >= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif check_p <= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            else:
                if check_p <= trade["tp"] and trade["tp"] > 0: trade["status"] = "Тейк ✅"; is_closed = True
                elif check_p >= trade["sl"] and trade["sl"] > 0: trade["status"] = "Стоп ❌"; is_closed = True
            if is_closed:
                trade["final_pnl"] = pnl_final

# Интерфейс
with st.sidebar:
    st.title("👤 Admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", value=None, placeholder="Цена...")
        qty = st.number_input("Кол-во монет", value=None, placeholder="Кол-во...")
        sl = st.number_input("Стоп-лосс", value=None, placeholder="Стоп...")
        tp = st.number_input("Тейк-профит", value=None, placeholder="Тейк...")
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - (sl if sl else entry))
                reward = abs((tp if tp else entry) - entry)
                rr = round(reward / risk, 2) if risk > 0 else 0.0
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": new_coin, "side": side, "entry": float(entry),
                    "qty": float(qty), "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, "rr": rr, 
                    "status": "В процессе ⏳", "final_pnl": None 
                })
                st.rerun()

tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    c1, c2, c3 = st.columns([1, 1, 2.5])
    with c1: 
        t_input = st.text_input("Тикер", value=st.session_state.ticker).upper()
        if t_input != st.session_state.ticker:
            st.session_state.ticker = t_input; st.rerun()
    with c2: st.selectbox("Биржа", ["Binance (Spot)"])
    with c3:
        st.write("Таймфрейм")
        tfs = ["5m", "15m", "1h", "4h", "1d"]
        cols = st.columns(len(tfs))
        for idx, tf_item in enumerate(tfs):
            if cols[idx].button(tf_item, key=f"tf_{tf_item}", type="primary" if st.session_state.tf == tf_item else "secondary", use_container_width=True):
                st.session_state.tf = tf_item; st.rerun()

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Цена {st.session_state.ticker}", f"${st.session_state.price:,.2f}")
    m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
    m3.metric("Активных", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

    if df_main is not None:
        fig = go.Figure(data=[go.Candlestick(x=df_main['time'], open=df_main['open'], high=df_main['high'], low=df_main['low'], close=df_main['close'])])
        fig.update_layout(
            template="plotly_dark", height=600, xaxis_rangeslider_visible=False, 
            margin=dict(l=0, r=50, t=0, b=0),
            yaxis=dict(side="right", tickformat="$.2f") # ЦЕНА СПРАВА
        )
        fig.add_hline(y=st.session_state.price, line_dash="dash", line_color="yellow")
        st.plotly_chart(fig, use_container_width=True)

with tab_journal:
    st.subheader("📓 Журнал")
    if st.session_state.trades:
        h = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
        names = ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "PnL ($)", "Статус", ""]
        for col, n in zip(h, names): col.markdown(f"**{n}**")
        for i, trade in enumerate(st.session_state.trades):
            pnl_disp = trade["final_pnl"] if trade["final_pnl"] is not None else (
                (st.session_state.price - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" and trade["coin"] == st.session_state.ticker else 0.0
            )
            cols = st.columns([1, 1, 0.8, 1, 1, 1, 1, 0.7, 1.2, 1, 0.5])
            cols[0].write(trade["time"]); cols[1].write(trade["coin"]); cols[2].write(trade["side"])
            cols[3].write(f"{trade['qty']}"); cols[4].write(f"{trade['entry']:.2f}")
            cols[5].write(f"{trade['sl']:.2f}"); cols[6].write(f"{trade['tp']:.2f}")
            cols[7].write(f"{trade['rr']}")
            p_color = "🟢" if (isinstance(pnl_disp, float) and pnl_disp >= 0) else "🔴"
            cols[8].write(f"{p_color} ${pnl_disp:.2f}")
            cols[9].write(trade["status"])
            if cols[10].button("🗑️", key=f"del_{trade['id']}"):
                st.session_state.trades.pop(i); st.rerun()

time.sleep(5)
st.rerun()
