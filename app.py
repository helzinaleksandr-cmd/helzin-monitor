import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'price' not in st.session_state: st.session_state.price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"
if 'ticker' not in st.session_state: st.session_state.ticker = "BTCUSDT"

def get_crypto_data(symbol, tf):
    ag = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    suffix = "histominute" if "m" in tf else "histohour" if "h" in tf else "histoday"
    
    if "USDC" in symbol: fsym, tsym = symbol.replace("USDC", ""), "USDC"
    else: fsym, tsym = symbol.replace("USDT", ""), "USDT"

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

# --- 2. САЙДБАР ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Нач. Депозит ($)", min_value=0.0, value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Открыть позицию")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип сделки", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Котировка", value=st.session_state.ticker).upper()
        entry = st.number_input("Цена входа", value=0.0, format="%.2f")
        qty = st.number_input("Кол-во монет", value=0.0, step=0.0001, format="%.4f")
        sl = st.number_input("Стоп-лосс (SL)", value=0.0, format="%.2f")
        tp = st.number_input("Тейк-профит (TP)", value=0.0, format="%.2f")
        
        if st.form_submit_button("ОТКРЫТЬ СДЕЛКУ", use_container_width=True):
            if entry > 0 and qty > 0:
                # Расчет RR
                risk = abs(entry - sl) if sl > 0 else 0
                reward = abs(tp - entry) if tp > 0 else 0
                rr_val = round(reward/risk, 2) if risk > 0 else 0
                
                st.session_state.trades.append({
                    "id": time.time(), 
                    "raw_time": datetime.now(),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": new_coin, "side": side, "entry": float(entry),
                    "qty": float(qty), "sl": float(sl), "tp": float(tp),
                    "rr": rr_val,
                    "status": "В процессе ⏳", "final_pnl": None 
                })
                st.rerun()

# --- 3. ТЕРМИНАЛ ---
@st.fragment(run_every=5)
def terminal_engine():
    df, cur_p = get_crypto_data(st.session_state.ticker, st.session_state.tf)
    if cur_p > 0: st.session_state.price = cur_p

    total_closed_pnl = 0.0
    closed_data = []
    
    for trade in st.session_state.trades:
        if "⏳" in trade["status"]:
            p_check = cur_p if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
            if p_check > 0:
                res = (p_check - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_check) * trade["qty"]
                if trade["side"] == "LONG":
                    if trade["tp"] > 0 and p_check >= trade["tp"]: trade["status"], trade["final_pnl"] = "Тейк ✅", res
                    elif trade["sl"] > 0 and p_check <= trade["sl"]: trade["status"], trade["final_pnl"] = "Стоп ❌", res
                else:
                    if trade["tp"] > 0 and p_check <= trade["tp"]: trade["status"], trade["final_pnl"] = "Тейк ✅", res
                    elif trade["sl"] > 0 and p_check >= trade["sl"]: trade["status"], trade["final_pnl"] = "Стоп ❌", res

        if trade["final_pnl"] is not None:
            total_closed_pnl += trade["final_pnl"]
            closed_data.append({"t": trade["raw_time"], "v": trade["final_pnl"]})

    t_trade, t_journal = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ И ЭКСПОРТ"])

    with t_trade:
        # ВЕРНУЛИ МЕТРИКИ (Депозит и Профит)
        c_p1, c_p2, c_p3 = st.columns([1.5, 1.5, 2])
        with c_p1:
            tin = st.text_input("Пара", value=st.session_state.ticker).upper()
            if tin != st.session_state.ticker: st.session_state.ticker = tin; st.rerun()
        with c_p2:
            st.metric("Баланс + PnL", f"${(st.session_state.balance + total_closed_pnl):,.2f}")
        with c_p3:
            st.metric("Чистый Профит", f"${total_closed_pnl:,.2f}", delta=f"{total_closed_pnl:+.2f}")

        # Цена и Таймфреймы
        c_h1, c_h2 = st.columns([1, 2])
        c_h1.write(f"## ${st.session_state.price:,.2f}")
        with c_h2:
            tcols = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if tcols[i].button(t, key=f"btn_{t}", type="primary" if st.session_state.tf == t else "secondary"):
                    st.session_state.tf = t; st.rerun()

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=10,t=0,b=0), xaxis_rangeslider_visible=False, yaxis_side="right")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📈 Аналитика PnL")
        period = st.radio("Период", ["День", "7 Дней", "Месяц", "Все"], horizontal=True)
        limit = datetime.now() - (timedelta(days=1) if period=="День" else timedelta(days=7) if period=="7 Дней" else timedelta(days=30) if period=="Месяц" else timedelta(days=365))
        pts = [st.session_state.balance]
        for d in [x for x in closed_data if x['t'] > limit]: pts.append(pts[-1] + d['v'])
        
        fig_p = go.Figure(go.Scatter(y=pts, mode='lines+markers', fill='tozeroy', line_color='#00FFCC'))
        fig_p.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=10,t=10,b=10), yaxis_side="right")
        st.plotly_chart(fig_p, use_container_width=True)

    with t_journal:
        if st.session_state.trades:
            csv = pd.DataFrame(st.session_state.trades).to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 СКАЧАТЬ CSV", data=csv, file_name="trades.csv", mime="text/csv")
            
            # ВЕРНУЛИ ВСЕ КОЛОНКИ: Вход, Стоп, RR
            cols = st.columns([1, 1, 0.6, 1, 1, 1, 0.5, 1, 1, 0.5])
            titles = ["Время", "Пара", "Тип", "Вход", "Стоп/Тейк", "PnL", "RR", "Статус", "Управление", ""]
            for col, t in zip(cols, titles): col.markdown(f"**{t}**")
            
            for i, tr in enumerate(st.session_state.trades):
                p_curr = st.session_state.price if tr["coin"] == st.session_state.ticker else get_crypto_data(tr["coin"], "5m")[1]
                p_now = tr["final_pnl"] if tr["final_pnl"] is not None else (p_curr - tr["entry"]) * tr["qty"] * (1 if tr["side"] == "LONG" else -1)
                
                c = st.columns([1, 1, 0.6, 1, 1, 1, 0.5, 1, 1, 0.5])
                c[0].write(tr["time"])
                c[1].write(tr["coin"])
                c[2].write(tr["side"])
                c[3].write(f"{tr['entry']:,.2f}")
                c[4].write(f"{tr['sl']:,.0f} / {tr['tp']:,.0f}")
                c[5].write(f"{'🟢' if p_now>=0 else '🔴'} ${p_now:.2f}")
                c[6].write(f"{tr.get('rr', 0)}")
                c[7].write(tr["status"])
                if "⏳" in tr["status"]:
                    if c[8].button("ЗАКРЫТЬ", key=f"c_{tr['id']}"):
                        tr["final_pnl"], tr["status"] = p_now, "Ручное ✋"
                        st.rerun()
                if c[9].button("🗑️", key=f"d_{tr['id']}"):
                    st.session_state.trades.pop(i); st.rerun()

terminal_engine()
