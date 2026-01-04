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
if 'equity_style' not in st.session_state:
    st.session_state.equity_style = "#00ff88"

def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), 
              "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    
    # ПРАВИЛЬНЫЙ ВЫБОР РЫНКА
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=1000&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        if 'Data' in res and 'Data' in res['Data']:
            df = pd.DataFrame(res['Data']['Data'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        return None
    except:
        return None

def check_trade_logic(current_price):
    changed = False
    for trade in st.session_state.trades:
        if trade['Статус'] == "OPEN":
            if trade['Тип'] == "LONG":
                if current_price >= trade['Тейк']:
                    trade['Статус'] = "✅ TAKE PROFIT"
                    changed = True
                elif current_price <= trade['Stop']:
                    trade['Статус'] = "❌ STOP LOSS"
                    changed = True
            elif trade['Тип'] == "SHORT":
                if current_price <= trade['Тейк']:
                    trade['Статус'] = "✅ TAKE PROFIT"
                    changed = True
                elif current_price >= trade['Stop']:
                    trade['Статус'] = "❌ STOP LOSS"
                    changed = True
    return changed

@st.fragment(run_every=3)
def live_chart_section(coin, tf, market_type):
    df = get_crypto_data(coin, tf, market_type)
    if df is not None:
        price_now = df['close'].iloc[-1]
        st.metric(f"{coin}/USDT ({market_type})", f"${price_now:,.2f}")
        
        if check_trade_logic(price_now):
            st.rerun()
            
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        )])
        
        # Линии сделок
        for trade in st.session_state.trades:
            if trade['Статус'] == "OPEN" and trade['Монета'] == coin:
                fig.add_hline(y=trade['Вход'], line_dash="solid", line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=trade['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                fig.add_hline(y=trade['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

        # ГИБКИЙ МАСШТАБ (Тяни шкалу справа!)
        fig.update_layout(
            template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10), dragmode='pan',
            yaxis=dict(side="right", fixedrange=False, autorange=True),
            xaxis=dict(fixedrange=False)
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

def render_equity_curve(period_label):
    st.subheader(f"📈 Доходность ({period_label})")
    closed_trades = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
    if not closed_trades:
        st.info("Нет закрытых сделок.")
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
                                   line=dict(color=st.session_state.equity_style, width=2), fill='tozeroy'))
    fig_equity.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(side="right"))
    st.plotly_chart(fig_equity, use_container_width=True)

# ИНТЕРФЕЙС
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    with st.form("login"):
        u = st.text_input("Логин")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if u == "admin" and p == "12345":
                st.session_state.logged_in = True
                st.rerun()
else:
    with st.sidebar:
        st.header("👤 admin")
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        with st.form("trade_form", clear_on_submit=True):
            t_side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
            t_coin = st.text_input("Монета", value="BTC").upper()
            t_entry = st.text_input("Вход", value="")
            t_amount = st.text_input("Кол-во", value="")
            t_stop = st.text_input("Стоп", value="")
            t_take = st.text_input("Тейк", value="")
            if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
                try:
                    e, a, s, tk = float(t_entry), float(t_amount), float(t_stop), float(t_take)
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(), "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": t_side, "Монета": t_coin, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk, 
                        "RR": round(abs(tk-e)/abs(e-s), 2) if abs(e-s)>0 else 0, 
                        "PL": f"+{abs(tk-e)*a:.2f}/-{abs(e-s)*a:.2f}",
                        "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                    })
                    st.rerun()
                except: st.error("Ошибка ввода")
        st.session_state.equity_style = st.color_picker("Цвет доходности", st.session_state.equity_style)
        if st.button("Выйти"):
            st.session_state.logged_in = False
            st.rerun()

    t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    with t1:
        c1, c2, c3 = st.columns([1, 1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_coin_input").upper()
        # ВЫБОР РЫНКА ТЕПЕРЬ РАБОТАЕТ
        m_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"], key="market_type_selector")
        with c3:
            st.write("Таймфрейм")
            bc = st.columns(5)
            tfs = ["5m", "15m", "1h", "4h", "1d"]
            for i, f in enumerate(tfs):
                if bc[i].button(f, key=f"tf_{f}", use_container_width=True):
                    st.session_state.timeframe = f
                    st.rerun()
        
        live_chart_section(active_coin, st.session_state.timeframe, m_type)
        st.divider()
        p_sel = st.radio("Период", ["Все время", "День", "Неделя", "Месяц"], horizontal=True)
        render_equity_curve(p_sel)

    with t2:
        if not st.session_state.trades: st.info("Пусто")
        else:
            cols = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
            for col, h in zip(cols, ["Время", "Тип", "Монета", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "P/L ($)", "Статус", "Del"]):
                col.write(f"**{h}**")
            for trade in reversed(st.session_state.trades):
                c = st.columns([1.2, 0.7, 0.7, 0.8, 1, 1, 1, 0.6, 1.4, 1.3, 0.6])
                data = [trade["Время"], trade["Тип"], trade["Монета"], str(trade["Кол-во"]), str(trade["Вход"]), str(trade["Stop"]), str(trade["Тейк"]), str(trade["RR"]), trade["PL"]]
                for i, v in enumerate(data): c[i].write(v)
                color = "green" if "TAKE" in trade["Статус"] else "red" if "STOP" in trade["Статус"] else "white"
                c[9].markdown(f":{color}[{trade['Статус']}]")
                if c[10].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades = [t for t in st.session_state.trades if t['id'] != trade['id']]
                    st.rerun()
