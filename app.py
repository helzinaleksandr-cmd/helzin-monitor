import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 1. НАСТРОЙКИ И ПАМЯТЬ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"
if 'ticker' not in st.session_state: st.session_state.ticker = "BTC"

def get_crypto_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    # Логика для работы с котировками типа BTCUSDT или BTCUSDC
    if "USDT" in symbol:
        fsym, tsym = symbol.replace("USDT", ""), "USDT"
    elif "USDC" in symbol:
        fsym, tsym = symbol.replace("USDC", ""), "USDC"
    else:
        fsym, tsym = symbol, "USDT"

    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={fsym}&tsym={tsym}&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('Response') == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df, float(df['close'].iloc[-1])
    except: return None, 0.0
    return None, 0.0

# --- 2. САЙДБАР (АДМИН-ПАНЕЛЬ) ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Начальный Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Открыть позицию")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип сделки", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Котировка (напр. BTCUSDT)", "BTCUSDT").upper()
        entry = st.number_input("Цена входа", value=0.0)
        qty = st.number_input("Кол-во монет", value=0.0, step=0.0001)
        sl = st.number_input("Стоп-лосс (SL)", value=0.0)
        tp = st.number_input("Тейк-профит (TP)", value=0.0)
        
        if st.form_submit_button("ОТКРЫТЬ СДЕЛКУ", use_container_width=True):
            if entry > 0 and qty > 0:
                risk = abs(entry - sl) if sl > 0 else 1.0
                reward = abs(tp - entry) if tp > 0 else 0.0
                st.session_state.trades.append({
                    "id": time.time(), 
                    "raw_time": datetime.now(),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "coin": new_coin, 
                    "side": side, 
                    "entry": float(entry),
                    "qty": float(qty), 
                    "sl": float(sl), 
                    "tp": float(tp), 
                    "rr": round(reward/risk, 2) if sl > 0 else 0.0, 
                    "status": "В процессе ⏳", 
                    "final_pnl": None 
                })
                st.rerun()

# --- 3. ОСНОВНОЙ ТЕРМИНАЛ ---
@st.fragment(run_every=5)
def terminal_engine():
    df, cur_p = get_crypto_data(st.session_state.ticker, st.session_state.tf)
    if cur_p > 0: st.session_state.price = cur_p

    total_closed_pnl = 0.0
    closed_trades_list = []
    
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            p_check = cur_p if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
            if p_check > 0:
                is_closed = False
                res = (p_check - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_check) * trade["qty"]
                if trade["side"] == "LONG":
                    if trade["tp"] > 0 and p_check >= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check <= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                else:
                    if trade["tp"] > 0 and p_check <= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check >= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                if is_closed: 
                    trade["final_pnl"] = res
                    trade["close_time"] = datetime.now()

        if trade["final_pnl"] is not None:
            total_closed_pnl += trade["final_pnl"]
            closed_trades_list.append({"time": trade.get("close_time", trade["raw_time"]), "pnl": trade["final_pnl"]})

    tab_trade, tab_journal = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ И ЭКСПОРТ"])

    with tab_trade:
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1: 
            t_in = st.text_input("Тикер", value=st.session_state.ticker).upper()
            if t_in != st.session_state.ticker: st.session_state.ticker = t_in; st.rerun()
        with c2: st.selectbox("Биржа", ["Binance"])
        with c3:
            st.write("Таймфрейм")
            t_cols = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if t_cols[i].button(t, key=f"tf_{t}", type="primary" if st.session_state.tf == t else "secondary"):
                    st.session_state.tf = t; st.rerun()

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {st.session_state.ticker}", f"${st.session_state.price:,.2f}")
        m2.metric("Баланс + Профит", f"${(st.session_state.balance + total_closed_pnl):,.2f}", f"{total_closed_pnl:+.2f}$")
        m3.metric("В рынке", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=50, t=0, b=0), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("📊 Аналитика")
        period = st.radio("Период", ["День", "7 Дней", "Месяц", "Полгода", "Все"], horizontal=True)
        now = datetime.now()
        if period == "День": start = now - timedelta(days=1)
        elif period == "7 Дней": start = now - timedelta(days=7)
        elif period == "Месяц": start = now - timedelta(days=30)
        elif period == "Полгода": start = now - timedelta(days=180)
        else: start = datetime(2000, 1, 1)

        filt = [t for t in closed_trades_list if t["time"] >= start]
        if filt:
            y_vals = [st.session_state.balance]
            for t in filt: y_vals.append(y_vals[-1] + t["pnl"])
            fig_p = go.Figure(go.Scatter(y=y_vals, mode='lines+markers', line=dict(color='#00FFCC', width=3), fill='tozeroy'))
            fig_p.update_layout(template="plotly_dark", height=200, margin=dict(l=0, r=50, t=10, b=10), yaxis=dict(side="right"))
            st.plotly_chart(fig_p, use_container_width=True)

    with tab_journal:
        # ЭКСПОРТ В CSV (Работает без дополнительных библиотек)
        if st.session_state.trades:
            df_export = pd.DataFrame(st.session_state.trades).drop(columns=['id', 'raw_time'], errors='ignore')
            csv = df_export.to_csv(index=False).encode('utf-8-sig') # utf-8-sig чтобы Excel видел русские буквы
            st.download_button(
                label="📥 СКАЧАТЬ ВЕСЬ ЖУРНАЛ (CSV для Excel)",
                data=csv,
                file_name=f"trading_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        st.subheader("📓 История сделок")
        if st.session_state.trades:
            for i, trade in enumerate(st.session_state.trades):
                p_curr = st.session_state.price if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
                p_disp = trade["final_pnl"] if trade["final_pnl"] is not None else (p_curr - trade["entry"]) * trade["qty"] * (1 if trade["side"] == "LONG" else -1)
                
                with st.expander(f"{trade['time']} | {trade['coin']} | {trade['side']} | PnL: ${p_disp:.2f} | {trade['status']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"Вход: {trade['entry']}")
                    c1.write(f"Кол-во: {trade['qty']}")
                    c2.write(f"SL: {trade['sl']}")
                    c2.write(f"TP: {trade['tp']}")
                    c3.write(f"RR: {trade['rr']}")
                    
                    if "⏳" in trade["status"]:
                        if st.button("ЗАКРЫТЬ ВРУЧНУЮ", key=f"cl_{trade['id']}"):
                            trade["final_pnl"], trade["status"], trade["close_time"] = p_disp, "Ручное ✋", datetime.now()
                            st.rerun()
                    if st.button("УДАЛИТЬ", key=f"del_{trade['id']}"):
                        st.session_state.trades.pop(i); st.rerun()
        else:
            st.info("Журнал пуст.")

terminal_engine()
