import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. Настройка терминала
st.set_page_config(page_title="Helzin Futures Pro", layout="wide")

# Инициализация данных в памяти
if 'trades' not in st.session_state: st.session_state.trades = []
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0
if 'tf' not in st.session_state: st.session_state.tf = "15m"

# 2. Функция получения данных (только ФЬЮЧЕРСЫ)
def get_data(symbol, tf):
    # Масштабируем таймфреймы для API
    mapping = {"5m": "histominute", "15m": "histominute", "1h": "histohour", "4h": "histohour", "1d": "histoday"}
    aggr = {"5m": 5, "15m": 15, "1h": 1, "4h": 4, "1d": 1}
    
    # Формируем правильный тикер для фьючерсов
    clean_symbol = symbol.replace("USDT", "")
    
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{mapping[tf]}?fsym={clean_symbol}&tsym=USDT&limit=200&aggregate={aggr[tf]}&e=BinanceFutures"
        res = requests.get(url, timeout=5).json()
        
        if res.get('Response') == 'Success':
            df = pd.DataFrame(res['Data']['Data'])
            if not df.empty:
                df['time'] = pd.to_datetime(df['time'], unit='s')
                st.session_state.last_price = float(df['close'].iloc[-1])
                return df
    except:
        return None
    return None

# 3. Боковая панель (Управление)
with st.sidebar:
    st.title("👨‍💻 ТЕРМИНАЛ")
    st.subheader("🚀 Новая позиция")
    
    with st.form("trade_form"):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", value="BTC").upper()
        # Поле входа берет текущую цену
        entry = st.number_input("Цена входа", value=float(st.session_state.last_price), format="%.2f")
        amount = st.text_input("Количество")
        sl = st.text_input("Стоп-лосс")
        tp = st.text_input("Тейк-профит")
        
        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            try:
                new_trade = {
                    "id": datetime.now().timestamp(),
                    "time": datetime.now().strftime("%H:%M"),
                    "side": side, "coin": coin, "entry": entry,
                    "amt": float(amount), "sl": float(sl), "tp": float(tp)
                }
                st.session_state.trades.append(new_trade)
                st.rerun()
            except:
                st.error("Ошибка в числах!")

# 4. Главный экран
# Сверху показываем цену и количество сделок
c1, c2, c3 = st.columns(3)
c1.metric("Binance Futures", f"${st.session_state.last_price:,.2f}")
c2.metric("Активных сделок", len(st.session_state.trades))
c3.metric("Рынок", "FUTURES")

# Выбор монеты и времени
col_t, col_tf = st.columns([1, 2])
current_coin = col_t.text_input("Тикер", "BTC").upper()

with col_tf:
    st.write("Таймфрейм")
    btns = st.columns(5)
    for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
        if btns[i].button(f, key=f, type="primary" if st.session_state.tf == f else "secondary"):
            st.session_state.tf = f; st.rerun()

# Загрузка графика
df = get_data(current_coin, st.session_state.tf)

if df is not None:
    # Отрисовка свечей
    fig = go.Figure(data=[go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#00ff88', decreasing_line_color='#ff4b4b'
    )])
    
    # Рисуем уровни сделок
    for t in st.session_state.trades:
        if t['coin'] == current_coin:
            fig.add_hline(y=t['entry'], line_color="white", annotation_text="ВХОД")
            fig.add_hline(y=t['tp'], line_dash="dash", line_color="#00ff88")
            fig.add_hline(y=t['sl'], line_dash="dash", line_color="#ff4b4b")

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=10, t=0, b=0), yaxis=dict(side="right", autorange=True))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Ожидание данных от Binance Futures... Попробуйте сменить таймфрейм.")

# Список сделок внизу
st.divider()
st.subheader("📑 Список открытых позиций")
if not st.session_state.trades:
    st.info("Нет открытых сделок")
else:
    for t in st.session_state.trades:
        r = st.columns([1, 1, 1, 1, 1, 0.5])
        r[0].write(t['time'])
        r[1].write(f"**{t['coin']} {t['side']}**")
        r[2].write(f"Вход: {t['entry']}")
        r[3].write(f"Кол-во: {t['amt']}")
        r[4].write(f"TP: {t['tp']} / SL: {t['sl']}")
        if r[5].button("🗑", key=t['id']):
            st.session_state.trades.remove(t); st.rerun()
