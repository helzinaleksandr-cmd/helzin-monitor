import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация состояний
if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0
if 'ticker' not in st.session_state: st.session_state.ticker = "BTC"
if 'market_type' not in st.session_state: st.session_state.market_type = "SPOT"
if 'tf' not in st.session_state: st.session_state.tf = "15m"

def get_binance_data(symbol, market_type, tf):
    # Очистка тикера: убираем пробелы и принудительно добавляем USDT
    symbol = symbol.strip().upper()
    if not symbol.endswith("USDT"):
        full_symbol = f"{symbol}USDT"
    else:
        full_symbol = symbol

    # Выбор правильного эндпоинта
    if market_type == "FUTURES":
        url = "https://fapi.binance.com/fapi/v1/klines"
    else:
        url = "https://api.binance.com/api/v3/klines"
    
    params = {"symbol": full_symbol, "interval": tf, "limit": 100}
    
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        
        # Если Binance вернул ошибку в JSON
        if isinstance(data, dict) and "code" in data:
            return None, 0.0
            
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close']: 
            df[col] = pd.to_numeric(df[col])
            
        return df, float(df['close'].iloc[-1])
    except Exception as e:
        return None, 0.0

# --- 2. САЙДБАР ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Нач. Депозит ($)", value=float(st.session_state.balance))
    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Тип", ["LONG", "SHORT"], horizontal=True)
        new_coin = st.text_input("Монета", value=st.session_state.ticker).upper()
        entry = st.number_input("Цена входа", value=0.0, format="%.4f")
        qty = st.number_input("Кол-во монет", value=0.0, step=0.0001, format="%.4f")
        sl = st.number_input("Стоп-лосс", value=0.0, format="%.4f")
        tp = st.number_input("Тейк-профит", value=0.0, format="%.4f")
        img_entry = st.file_uploader("🖼 Скриншот (ВХОД)", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if entry > 0 and qty > 0:
                st.session_state.trades.append({
                    "id": time.time(), "time": datetime.now(),
                    "coin": new_coin, "market": st.session_state.market_type, "side": side, 
                    "entry": entry, "qty": qty, "sl": sl, "tp": tp, 
                    "status": "В процессе ⏳", "final_pnl": None, 
                    "img_entry": img_entry, "img_exit": None
                })
                st.rerun()

# --- 3. ОСНОВНОЙ ИНТЕРФЕЙС ---
# Мы НЕ используем fragment для заголовка, чтобы тикер обновлялся мгновенно
c1, c2, c3 = st.columns([1, 1, 2.5])
with c1: 
    new_t = st.text_input("Тикер", value=st.session_state.ticker).upper()
    if new_t != st.session_state.ticker:
        st.session_state.ticker = new_t
        st.rerun()
with c2:
    m_choice = st.selectbox("Рынок", ["SPOT", "FUTURES"], 
                            index=0 if st.session_state.market_type == "SPOT" else 1)
    if m_choice != st.session_state.market_type:
        st.session_state.market_type = m_choice
        st.rerun()
with c3:
    st.write("Таймфрейм")
    tc = st.columns(5)
    tfs = ["5m", "15m", "1h", "4h", "1d"]
    for i, t in enumerate(tfs):
        if tc[i].button(t, key=f"btn_{t}", type="primary" if st.session_state.tf == t else "secondary"):
            st.session_state.tf = t
            st.rerun()

# А теперь сам график в фрагменте для автообновления
@st.fragment(run_every=5)
def draw_main_content():
    df, cur_p = get_binance_data(st.session_state.ticker, st.session_state.market_type, st.session_state.tf)
    
    # Метрики
    total_pnl = sum([t['final_pnl'] for t in st.session_state.trades if t['final_pnl'] is not None])
    m1, m2, m3 = st.columns(3)
    
    if cur_p > 0:
        m1.metric(f"Цена {st.session_state.ticker} ({st.session_state.market_type})", f"${cur_p:,.2f}")
    else:
        m1.error("Ошибка тикера")
        
    m2.metric("Баланс + PnL", f"${(st.session_state.balance + total_pnl):,.2f}")
    m3.metric("Профит сессии", f"${total_pnl:+.2f}")

    if df is not None:
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], 
            low=df['low'], close=df['close'],
            increasing_line_color='#00ffad', decreasing_line_color='#ff3e3e'
        )])
        fig.update_layout(
            template="plotly_dark", height=500, 
            margin=dict(l=0, r=50, t=10, b=10),
            yaxis=dict(side="right", gridcolor="#333"),
            xaxis=dict(gridcolor="#333"),
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Не удалось загрузить данные. Проверьте правильность тикера (например: BTC, ETH, SOL)")

# Вызов отрисовки
draw_main_content()

# Вкладки Журнала и Статистики ниже (вне фрагмента обновления графика)
tab_j, tab_s = st.tabs(["📓 ЖУРНАЛ СДЕЛОК", "📊 СТАТИСТИКА"])
with tab_j:
    if not st.session_state.trades:
        st.info("Сделок пока нет.")
    for i, trade in enumerate(st.session_state.trades):
        with st.expander(f"{trade['coin']} | {trade['side']} | PnL: {trade.get('final_pnl', '0.0')}"):
            st.write(f"Вход: {trade['entry']} | Рынок: {trade['market']}")
            if st.button("Удалить", key=f"del_{trade['id']}"):
                st.session_state.trades.pop(i)
                st.rerun()
