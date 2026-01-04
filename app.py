import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# 1. Настройка страницы
st.set_page_config(page_title="Helzin Terminal", layout="wide")

# 2. Инициализация базы
DB_FILE = "trades_history.json"

for key in ['trades', 'deposit', 'logged_in', 'timeframe', 'last_price', 'active_coin']:
    if key not in st.session_state:
        if key == 'trades': st.session_state.trades = []
        elif key == 'deposit': st.session_state.deposit = 1000.0
        elif key == 'logged_in': st.session_state.logged_in = False
        elif key == 'timeframe': st.session_state.timeframe = "15m"
        elif key == 'last_price': st.session_state.last_price = 0.0
        elif key == 'active_coin': st.session_state.active_coin = "BTC"

if not st.session_state.trades and os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.trades = data.get("trades", [])
    except: pass

def save_data():
    try:
        data = {"trades": st.session_state.trades, "deposit": st.session_state.deposit}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# 3. Ультимативная функция загрузки данных (Spot + Futures)
def fetch_data(ticker, tf, m_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    
    # Для фьючерсов пробуем разные варианты биржи/тикера
    exchanges = ["Binance"] if m_type == "SPOT" else ["BinanceFutures", "Bitmex"]
    
    for ex in exchanges:
        try:
            url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=500&aggregate={aggregate}&e={ex}"
            res = requests.get(url, timeout=5).json()
            if res.get('Response') == 'Success':
                df = pd.DataFrame(res['Data']['Data'])
                if not df.empty:
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    st.session_state.last_price = float(df['close'].iloc[-1])
                    return df
        except: continue
    return None

# 4. Интерфейс
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    if st.button("Войти в систему", use_container_width=True): 
        st.session_state.logged_in = True
        st.rerun()
else:
    with st.sidebar:
        st.header("👤 admin")
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        st.subheader("➕ Новая сделка")
        
        with st.form("trade_form"):
            side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
            # При вводе монеты она сразу сохраняется в стейт
            c_input = st.text_input("Монета", value=st.session_state.active_coin).upper()
            ent = st.text_input("Вход", value=str(st.session_state.last_price))
            amt = st.text_input("Кол-во монет")
            sl = st.text_input("Стоп")
            tp = st.text_input("Тейк")
            
            if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
                try:
                    e, a, s, tk = [float(x.replace(',','.')) for x in [ent, amt, sl, tp]]
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": side, "Монета": c_input, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk,
                        "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                    })
                    save_data(); st.rerun()
                except: st.error("Ошибка в числах!")

        if st.button("Выход"): 
            st.session_state.logged_in = False
            st.rerun()

    t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    
    with t1:
        c1, c2, c3 = st.columns([1, 1, 3])
        # Синхронизируем ввод монеты
        active_coin = c1.text_input("Тикер", value=st.session_state.active_coin).upper()
        st.session_state.active_coin = active_coin
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
        
        with c3:
            st.write("Таймфрейм")
            ts = st.columns(5)
            for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if ts[i].button(f, key=f"tf_{f}", type="primary" if st.session_state.timeframe == f else "secondary"):
                    st.session_state.timeframe = f; st.rerun()

        # Загрузка данных
        df = fetch_data(active_coin, st.session_state.timeframe, m_type)

        # Метрики
        closed = [t for t in st.session_state.trades if t['Статус'] != "OPEN"]
        total_pnl = sum([(t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num']) for t in closed])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Текущая цена", f"${st.session_state.last_price:,.2f}")
        m2.metric("Общий P/L", f"${total_pnl:,.2f}")
        m3.metric("Активных", len([t for t in st.session_state.trades if t['Статус'] == "OPEN"]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            for tr in st.session_state.trades:
                if tr['Статус'] == "OPEN" and tr['Монета'] == active_coin:
                    fig.add_hline(y=tr['Вход'], line_color="white")
                    fig.add_hline(y=tr['Тейк'], line_dash="dash", line_color="#00ff88")
                    fig.add_hline(y=tr['Stop'], line_dash="dash", line_color="#ff4b4b")
            fig.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False, 
                              yaxis=dict(side="right", autorange=True))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"⚠️ Не удалось загрузить график {active_coin} ({m_type}). Проверьте тикер.")

        st.subheader("📈 Доходность")
        if closed:
            bal = [st.session_state.deposit]
            curr = st.session_state.deposit
            for t in sorted(closed, key=lambda x: x['id']):
                curr += (t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num'])
                bal.append(curr)
            st.line_chart(bal)

    with t2:
        if not st.session_state.trades: st.info("Журнал пуст")
        else:
            for tr in reversed(st.session_state.trades):
                c = st.columns([1, 1, 1, 1, 1, 0.5])
                c[0].write(tr['Время'])
                c[1].write(tr['Монета'])
                c[2].write(f"${tr['Вход']}")
                c[3].write(str(tr['Кол-во']))
                status_color = "green" if "PROFIT" in tr['Статус'] else "red" if "LOSS" in tr['Статус'] else "white"
                c[4].markdown(f":{status_color}[{tr['Статус']}]")
                if c[5].button("🗑️", key=f"del_{tr['id']}"):
                    st.session_state.trades.remove(tr); save_data(); st.rerun()
            
            if st.button("🔥 ОЧИСТИТЬ ВСЁ", use_container_width=True):
                st.session_state.trades = []; save_data(); st.rerun()
