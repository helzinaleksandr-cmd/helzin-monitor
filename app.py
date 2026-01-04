import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Настройка страницы
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

# Инициализация состояния
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0
if 'price' not in st.session_state:
    st.session_state.price = 0.0
if 'tf' not in st.session_state:
    st.session_state.tf = "1h"

# Маппинг монет CoinGecko ID (добавь новые при необходимости)
COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "TRX": "tron",
    "TON": "toncoin", "LINK": "chainlink", "AVAX": "avalanche-2", "SHIB": "shiba-inu"
}

# Новая функция получения данных через CoinGecko (бесплатно, без ключа!)
def get_data(symbol, tf):
    symbol = symbol.upper()
    if symbol not in COINGECKO_IDS:
        return None, 0.0

    coin_id = COINGECKO_IDS[symbol]

    # Параметры для разных ТФ
    if tf in ["5m", "15m"]:
        days = 1  # Для коротких — последние сутки (максимум детализации)
    elif tf == "1h":
        days = 7
    elif tf == "4h":
        days = 30
    elif tf == "1d":
        days = 365  # До года исторических данных бесплатно
    else:
        days = 90

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "hourly" if days <= 90 else "daily"}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "prices" not in data or not data["prices"]:
            return None, 0.0

        # Создаём DataFrame
        df = pd.DataFrame(data["prices"], columns=["time", "close"])
        df["open"] = df["close"].shift(1).fillna(df["close"])
        df["high"] = df[["open", "close"]].max(axis=1)
        df["low"] = df[["open", "close"]].min(axis=1)
        df["time"] = pd.to_datetime(df["time"], unit='ms')

        current_price = df["close"].iloc[-1]
        st.session_state.price = float(current_price)

        return df, float(current_price)
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return None, 0.0

# === SIDEBAR ===
with st.sidebar:
    st.title("👤 admin")
    st.session_state.balance = st.number_input("Депозит ($)", min_value=0.0, value=st.session_state.balance)

    st.divider()
    st.subheader("➕ Новая сделка")
    with st.form("trade_form", clear_on_submit=True):
        side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
        coin = st.text_input("Монета", "BTC").upper()
        entry = st.number_input("Цена входа", min_value=0.0, format="%.2f")
        qty = st.number_input("Кол-во монет", min_value=0.0, step=0.001)
        sl = st.number_input("Стоп", min_value=0.0, format="%.2f")
        tp = st.number_input("Тейк", min_value=0.0, format="%.2f")

        if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
            if qty > 0 and entry > 0:
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = round(reward / risk, 2) if risk > 0 else 0.0

                st.session_state.trades.append({
                    "id": time.time(),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "coin": coin,
                    "side": side,
                    "entry": entry,
                    "qty": qty,
                    "sl": sl,
                    "tp": tp,
                    "rr": rr,
                    "status": "В процессе ⏳"
                })
                st.success(f"{side} {coin} открыт!")
                st.rerun()

# === ОСНОВНЫЕ ВКЛАДКИ ===
tab_trade, tab_journal = st.tabs(["🕯 Торговля", "📓 Журнал"])

with tab_trade:
    col1, col2 = st.columns([1, 2])
    with col1:
        ticker = st.text_input("Тикер", value="BTC", key="ticker_input").upper()
    with col2:
        st.write("Таймфрейм")
        tf_cols = st.columns(5)
        timeframes = ["5m", "15m", "1h", "4h", "1d"]
        for i, tf in enumerate(timeframes):
            if tf_cols[i].button(tf, key=f"tf_btn_{tf}"):
                st.session_state.tf = tf
                st.rerun()

    if st.button("🔄 Обновить график и цену"):
        st.rerun()

    df, current_price = get_data(ticker, st.session_state.tf)

    # Метрики
    m1, m2, m3 = st.columns(3)
    m1.metric("Текущая цена", f"${current_price:,.2f}" if current_price > 0 else "—")
    m2.metric("Депозит", f"${st.session_state.balance:,.2f}")
    m3.metric("Активных сделок", len([t for t in st.session_state.trades if "⏳" in t['status']]))

    # График
    if df is not None and not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        )])

        fig.update_layout(
            title=f"{ticker}/USDT — {st.session_state.tf} (данные CoinGecko)",
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis_title="Время",
            yaxis_title="Цена (USD)"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"⚠️ Нет данных для {ticker}")
        st.info("Поддерживаемые монеты: BTC, ETH, SOL, BNB, XRP, ADA, DOGE и другие популярные.\nНажми 🔄 для повторной попытки.")

# === ЖУРНАЛ === (остался почти без изменений)
with tab_journal:
    st.subheader("📓 Журнал сделок")

    if st.session_state.trades:
        headers = st.columns([1, 1, 1, 1, 1, 1, 0.8, 1.2, 1, 0.5])
        header_names = ["Время", "Актив", "Тип", "
