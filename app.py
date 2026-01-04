import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Helzin Trading Terminal", layout="wide")

# Инициализация сессии
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'deposit' not in st.session_state:
    st.session_state.deposit = 1000.0
if 'timeframe' not in st.session_state:
    st.session_state.timeframe = "15m"

def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=150&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except:
        return None

def check_trade_logic(trades, current_price):
    for trade in trades:
        if trade['Статус'] == "OPEN":
            if trade['Тип'] == "LONG":
                if current_price >= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price <= trade['Stop']: trade['Статус'] = "❌ STOP LOSS"
            else:
                if current_price <= trade['Тейк']: trade['Статус'] = "✅ TAKE PROFIT"
                elif current_price >= trade['Stop']: trade['Статус'] = "❌ STOP LOSS"

@st.fragment(run_every=3)
def live_chart_section(coin, tf, market_type):
    df = get_crypto_data(coin, tf, market_type)
    if df is not None:
        price_now = df['close'].iloc[-1]
        st.metric(f"{coin}/USDT ({market_type})", f"${price_now:,.2f}")
        check_trade_logic(st.session_state.trades, price_now)
        
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                                          increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, 
                          margin=dict(l=10, r=10, t=10, b=10), dragmode='pan', yaxis=dict(side="right", fixedrange=False))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

def render_equity_curve():
    st.subheader("📈 Кривая доходности")
    closed_trades = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
    if not closed_trades:
        st.info("Нет закрытых сделок для анализа.")
        return
    history = [{"time": datetime.now() - timedelta(minutes=10), "balance": st.session_state.deposit}]
    current_bal = st.session_state.deposit
    for t in sorted(closed_trades, key=lambda x: x['id']):
        profit_val = t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num']
        current_bal += profit_val
        history.append({"time": datetime.fromtimestamp(t['id']), "balance": current_bal})
    df_equity = pd.DataFrame(history)
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(x=df_equity['time'], y=df_equity['balance'], mode='lines+markers', 
                                   line=dict(color='#00ff88', width=3), fill='tozeroy', 
                                   fillcolor='rgba(0, 255, 136, 0.1)', name="Баланс"))
    fig_equity.update_layout(template="plotly_dark", height=250, margin=dict(l=10, r=10, t=10, b=10),
                            yaxis=dict(side="right"), xaxis=dict(showgrid=False))
    st.plotly_chart(fig_equity, use_container_width=True)

# БЛОК ВХОДА
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    with st.form("login_form"):
        u = st.text_input("Логин")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if u == "admin" and p == "12345":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Ошибка входа")
else:
    with st.sidebar:
        st.header(f"👤 admin")
        st.session_state.deposit = st.number_input("Начальный Депозит ($)", value=float(st.session_state.deposit), format="%.2f")
        st.divider()
        st.subheader("➕ Новая сделка")
        
        with st.form("trade_form", clear_on_submit=True):
            t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
            t_coin = st.text_input("Монета", value="BTC").upper()
            
            # УБРАЛ PLACEHOLDER, ЧТОБЫ ТЕКСТ НЕ НАКЛАДЫВАЛСЯ
            t_entry = st.number_input("Вход", value=None)
            t_amount = st.number_input("Кол-во", value=None)
            t_stop = st.number_input("Стоп", value=None)
            t_take = st.number_input("Тейк", value=None)
            
            if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
                if t_entry and t_stop and t_take and t_amount:
                    risk = abs(t_entry - t_stop)
                    reward = abs(t_take - t_entry)
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(),
                        "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": t_side, "Монета": t_coin, "Кол-во": t_amount,
                        "Вход": t_entry, "Stop": t_stop, "Тейк": t_take, 
                        "RR": round(reward/risk, 2) if risk > 0 else 0,
                        "PL": f"+{reward * t_amount:.2f}/-{risk * t_amount:.2f}",
                        "profit_num": reward * t_amount,
                        "loss_num": risk * t_amount,
                        "Статус": "OPEN"
                    })
                    st.rerun()
                else: st.error("Заполни все поля!")
        
        if st.button("Выйти"):
            st.session_state.logged_in = False
            st.rerun()

    tab1, tab2 = st.tabs(["🕯 Торговля", "📑 Журнал"])

    with tab1:
        c1, c2, c3 = st.columns([1, 1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_coin").upper()
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"])
        with c3:
            st.write("Таймфрейм")
            btn_cols = st.columns(5)
            tfs = ["5m", "15m", "1h", "4h", "1d"]
            for i, tf_btn in enumerate(tfs):
                if btn_cols[i].button(tf_btn, use_container_width=True, type="primary" if st.session_state.timeframe == tf_btn else "secondary"):
                    st.session_state.timeframe = tf_btn
                    st.rerun()
        
        live_chart_section(active_coin, st.session_state.timeframe, m_type)
        st.divider()
        render_equity_curve()

    with tab2:
        if not st.session_state.trades:
            st.info("Журнал пуст")
        else:
            # Скорректировал ширину колонок, чтобы текст не слипался
            cols = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
            headers = ["Время", "Тип", "Монета", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "P/L ($)", "Статус", "Del"]
            for col, h in zip(cols, headers): col.write(f"**{h}**")
            for trade in reversed(st.session_state.trades):
                c = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
                c[0].write(trade["Время"])
                c[1].write(trade["Тип"])
                c[2].write(trade["Монета"])
                c[3].write(str(trade["Кол-во"]))
                c[4].write(str(trade["Вход"]))
                c[5].write(str(trade["Stop"]))
                c[6].write(str(trade["Тейк"]))
                c[7].write(str(trade["RR"]))
                c[8].write(trade["PL"])
                color = "green" if "TAKE" in trade["Статус"] else "red" if "STOP" in trade["Статус"] else "white"
                c[9].markdown(f":{color}[{trade['Статус']}]")
                if c[10].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades = [t for t in st.session_state.trades if t['id'] != trade['id']]
                    st.rerun()
