import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
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
    url = f"https://min-api.cryptocompare.com/data/v2/{suffix}?fsym={symbol}&tsym=USDT&limit=100&aggregate={ag.get(tf, 15)}&e=Binance"
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
        new_coin = st.text_input("Монета (напр. SOL)", "BTC").upper()
        entry = st.number_input("Цена входа", value=None, placeholder="0.0")
        qty = st.number_input("Кол-во монет", value=None, placeholder="0.0", step=0.0001)
        sl = st.number_input("Стоп-лосс (SL)", value=None, placeholder="0.0")
        tp = st.number_input("Тейк-профит (TP)", value=None, placeholder="0.0")
        
        if st.form_submit_button("ОТКРЫТЬ СДЕЛКУ", use_container_width=True):
            if entry and qty:
                risk = abs(entry - (sl if sl else entry))
                reward = abs((tp if tp else entry) - entry)
                st.session_state.trades.append({
                    "id": time.time(), 
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": new_coin, 
                    "side": side, 
                    "entry": float(entry),
                    "qty": float(qty), 
                    "sl": float(sl) if sl else 0.0, 
                    "tp": float(tp) if tp else 0.0, 
                    "rr": round(reward/risk, 2) if risk > 0 else 0.0, 
                    "status": "В процессе ⏳", 
                    "final_pnl": None 
                })
                st.rerun()

# --- 3. ОСНОВНОЙ ТЕРМИНАЛ (ОБНОВЛЕНИЕ 5 СЕК) ---
@st.fragment(run_every=5)
def terminal_engine():
    # Получаем актуальную цену
    df, cur_p = get_crypto_data(st.session_state.ticker, st.session_state.tf)
    if cur_p > 0: st.session_state.price = cur_p

    # Логика автоматического закрытия и расчет PnL
    total_closed_pnl = 0.0
    pnl_history = [st.session_state.balance]
    
    for trade in st.session_state.trades:
        # Если сделка активна — проверяем цену
        if "⏳" in trade["status"]:
            # Если монета сделки совпадает с графиком — берем цену графика, иначе тянем отдельно
            p_check = cur_p if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
            
            if p_check > 0:
                is_closed = False
                current_res = (p_check - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_check) * trade["qty"]
                
                # Проверка SL/TP
                if trade["side"] == "LONG":
                    if trade["tp"] > 0 and p_check >= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check <= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                else:
                    if trade["tp"] > 0 and p_check <= trade["tp"]: trade["status"] = "Тейк ✅"; is_closed = True
                    elif trade["sl"] > 0 and p_check >= trade["sl"]: trade["status"] = "Стоп ❌"; is_closed = True
                
                if is_closed: trade["final_pnl"] = current_res

        # Суммируем закрытый профит для кривой доходности
        if trade["final_pnl"] is not None:
            total_closed_pnl += trade["final_pnl"]
            pnl_history.append(st.session_state.balance + total_closed_pnl)

    # --- ВИЗУАЛ (ВКЛАДКИ) ---
    tab_trade, tab_journal = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ СДЕЛОК"])

    with tab_trade:
        # Панель инструментов
        c1, c2, c3 = st.columns([1, 1, 2.5])
        with c1: 
            t_in = st.text_input("Тикер", value=st.session_state.ticker).upper()
            if t_in != st.session_state.ticker: st.session_state.ticker = t_in; st.rerun()
        with c2: st.selectbox("Биржа", ["Binance (Spot)"])
        with c3:
            st.write("Таймфрейм")
            t_cols = st.columns(5)
            for i, t in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if t_cols[i].button(t, key=f"tf_{t}", type="primary" if st.session_state.tf == t else "secondary"):
                    st.session_state.tf = t; st.rerun()

        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Цена {st.session_state.ticker}", f"${st.session_state.price:,.2f}")
        m2.metric("Баланс + Профит", f"${(st.session_state.balance + total_closed_pnl):,.2f}", f"{total_closed_pnl:+.2f}$")
        m3.metric("В рынке", len([t for t in st.session_state.trades if "⏳" in t["status"]]))

        # ГЛАВНЫЙ ГРАФИК
        if df is not None:
            fig_chart = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig_chart.update_layout(
                template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=50, t=0, b=0),
                yaxis=dict(side="right", tickformat="$.2f") # Цена справа
            )
            fig_chart.add_hline(y=st.session_state.price, line_dash="dash", line_color="yellow")
            st.plotly_chart(fig_chart, use_container_width=True)

        # КРИВАЯ ДОХОДНОСТИ (Equity)
        st.subheader("📈 Динамика счета (PnL)")
        fig_pnl = go.Figure(go.Scatter(y=pnl_history, mode='lines+markers', line=dict(color='#00FFCC', width=3), fill='tozeroy'))
        fig_pnl.update_layout(
            template="plotly_dark", height=200, margin=dict(l=0, r=50, t=10, b=10),
            yaxis=dict(side="right"), xaxis=dict(title="Сделки по порядку")
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    with tab_journal:
        st.subheader("📓 История и управление сделками")
        if st.session_state.trades:
            # Сетка таблицы
            h = st.columns([1, 0.8, 0.6, 0.8, 0.8, 0.8, 0.8, 0.5, 1, 1, 1, 0.4])
            names = ["Время", "Актив", "Тип", "Кол-во", "Вход", "Стоп", "Тейк", "RR", "PnL ($)", "Статус", "Действие", ""]
            for col, n in zip(h, names): col.markdown(f"**{n}**")
            
            for i, trade in enumerate(st.session_state.trades):
                # Расчет текущего PnL для отображения в таблице
                if trade["final_pnl"] is not None:
                    p_disp = trade["final_pnl"]
                else:
                    p_curr = st.session_state.price if trade["coin"] == st.session_state.ticker else get_crypto_data(trade["coin"], "5m")[1]
                    p_disp = (p_curr - trade["entry"]) * trade["qty"] if trade["side"] == "LONG" else (trade["entry"] - p_curr) * trade["qty"]
                
                cols = st.columns([1, 0.8, 0.6, 0.8, 0.8, 0.8, 0.8, 0.5, 1, 1, 1, 0.4])
                cols[0].write(trade["time"])
                cols[1].write(trade["coin"])
                cols[2].write(trade["side"])
                cols[3].write(f"{trade['qty']}")
                cols[4].write(f"{trade['entry']:,.2f}")
                cols[5].write(f"{trade['sl']:,.2f}")
                cols[6].write(f"{trade['tp']:,.2f}")
                cols[7].write(f"{trade['rr']}")
                
                p_color = "🟢" if p_disp >= 0 else "🔴"
                cols[8].write(f"{p_color} ${p_disp:.2f}")
                cols[9].write(trade["status"])
                
                # КНОПКА ЗАКРЫТИЯ (ДЛЯ АКТИВНЫХ)
                if "⏳" in trade["status"]:
                    if cols[10].button("ЗАКРЫТЬ", key=f"cl_{trade['id']}", type="primary"):
                        trade["final_pnl"] = p_disp
                        trade["status"] = "Ручное ✋"
                        st.rerun()
                else:
                    cols[10].write("Закрыта")
                
                # УДАЛЕНИЕ
                if cols[11].button("🗑️", key=f"del_{trade['id']}"):
                    st.session_state.trades.pop(i)
                    st.rerun()
        else:
            st.info("Журнал пуст. Откройте сделку в сайдбаре.")

# ЗАПУСК
terminal_engine()
