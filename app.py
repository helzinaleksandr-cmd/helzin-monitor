import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

DB_FILE = "trades_history.json"

def save_data():
    data = {"trades": st.session_state.trades, "deposit": st.session_state.deposit}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.trades = data.get("trades", [])
                st.session_state.deposit = data.get("deposit", 1000.0)
        except: pass

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = []
    load_data()
if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"
if 'equity_style' not in st.session_state: st.session_state.equity_style = "#00ff88"
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0

def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=1000&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        st.session_state.last_price = float(df['close'].iloc[-1])
        return df
    except: return None

def check_trade_logic(current_price):
    changed = False
    for trade in st.session_state.trades:
        if trade['Статус'] == "OPEN":
            if trade['Тип'] == "LONG":
                if current_price >= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"; changed = True
                elif current_price <= trade['Stop']: trade['Статус'] = "❌ STOP LOSS"; changed = True
            else:
                if current_price <= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"; changed = True
                elif current_price >= trade['Stop']: trade['Статус'] = "❌ STOP LOSS"; changed = True
    if changed: save_data()
    return changed

@st.fragment(run_every=3)
def live_chart_section(coin, tf, market_type):
    df = get_crypto_data(coin, tf, market_type)
    if df is not None:
        price_now = st.session_state.last_price
        closed = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
        wins = len([t for t in closed if "PROFIT" in t['Статус']])
        total_pnl = sum([(t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num']) for t in closed])
        winrate = (wins / len(closed) * 100) if len(closed) > 0 else 0
        open_trades = len([t for t in st.session_state.trades if t['Статус'] == "OPEN"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Цена", f"${price_now:,.2f}")
        m2.metric("P/L Общий", f"${total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")
        m3.metric("Win Rate", f"{winrate:.1f}%")
        m4.metric("Позиции", open_trades)

        if check_trade_logic(price_now): st.rerun()
            
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                                          increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        
        for trade in st.session_state.trades:
            if trade['Статус'] == "OPEN" and trade['Монета'] == coin:
                fig.add_hline(y=trade['Вход'], line_dash="solid", line_color="white", annotation_text="ВХОД")
                fig.add_hline(y=trade['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                fig.add_hline(y=trade['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

        fig.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10),
                          dragmode='pan', yaxis=dict(side="right", fixedrange=False, autorange=True), xaxis=dict(fixedrange=False))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

def render_equity_curve(period_label):
    st.subheader(f"📈 Доходность ({period_label})")
    closed = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
    if not closed: return
    history = [{"time": datetime.now() - timedelta(minutes=5), "balance": st.session_state.deposit}]
    curr = st.session_state.deposit
    for t in sorted(closed, key=lambda x: x['id']):
        curr += (t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num'])
        history.append({"time": datetime.fromtimestamp(t['id']), "balance": curr})
    df_e = pd.DataFrame(history)
    fig = go.Figure(go.Scatter(x=df_e['time'], y=df_e['balance'], mode='lines+markers', line=dict(color=st.session_state.equity_style, width=3), fill='tozeroy'))
    fig.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(side="right"))
    st.plotly_chart(fig, use_container_width=True)

if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    if st.button("Войти как admin"): st.session_state.logged_in = True; st.rerun()
else:
    with st.sidebar:
        st.header("👤 admin")
        st.session_state.deposit = st.number_input("Нач. Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        st.subheader("➕ Новая сделка")
        
        # Отключаем автозаполнение через autocomplete="off"
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        coin_input = st.text_input("Монета", value="BTC", autocomplete="off").upper()
        
        # Авто-подстановка текущей цены для удобства
        curr_p = st.session_state.last_price
        ent = st.text_input("Вход", value=str(curr_p) if curr_p > 0 else "", autocomplete="off")
        amt = st.text_input("Кол-во", autocomplete="off")
        sl = st.text_input("Стоп", autocomplete="off")
        tp = st.text_input("Тейк", autocomplete="off")
        
        if st.button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            try:
                # Проверка на пустые поля
                if not all([ent, amt, sl, tp]):
                    st.error("Заполните все поля!")
                else:
                    e, a, s, tk = float(ent.replace(',','.')), float(amt.replace(',','.')), float(sl.replace(',','.')), float(tp.replace(',','.'))
                    st.session_state.trades.append({"id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": side, "Монета": coin_input, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk, 
                        "RR": round(abs(tk-e)/abs(e-s), 2) if abs(e-s)>0 else 0, "PL": f"+{abs(tk-e)*a:.2f}/-{abs(e-s)*a:.2f}",
                        "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"})
                    save_data(); st.rerun()
            except ValueError:
                st.error("Используйте только цифры и точки!")

        st.divider()
        st.session_state.equity_style = st.color_picker("Цвет прибыли", st.session_state.equity_style)
        if st.button("Выход"): st.session_state.logged_in = False; st.rerun()

    t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    with t1:
        c1, c2, c3 = st.columns([1, 1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="active_coin_idx").upper()
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
        with c3:
            st.write("Таймфрейм")
            bc = st.columns(5)
            for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if bc[i].button(f, type="primary" if st.session_state.timeframe == f else "secondary", key=f"tf_b_{f}", use_container_width=True):
                    st.session_state.timeframe = f; st.rerun()
        
        live_chart_section(active_coin, st.session_state.timeframe, m_type)
        st.divider()
        p_sel = st.radio("Статистика за:", ["Все время", "День", "Неделя", "Месяц"], horizontal=True)
        render_equity_curve(p_sel)

    with t2:
        if not st.session_state.trades: st.info("Пусто")
        else:
            cols = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
            for col, h in zip(cols, ["Время", "Тип", "Монета", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "P/L", "Статус", "Del"]): col.write(f"**{h}**")
            for tr in reversed(st.session_state.trades):
                c = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
                d = [tr["Время"], tr["Тип"], tr["Монета"], str(tr["Кол-во"]), str(tr["Вход"]), str(tr["Stop"]), str(tr["Тейк"]), str(tr["RR"]), tr["PL"]]
                for i, v in enumerate(d): c[i].write(v)
                clr = "green" if "TAKE" in tr["Статус"] else "red" if "STOP" in tr["Статус"] else "white"
                c[9].markdown(f":{clr}[{tr['Статус']}]")
                if c[10].button("🗑️", key=tr["id"]):
                    st.session_state.trades = [t for t in st.session_state.trades if t['id'] != tr['id']]; save_data(); st.rerun()
