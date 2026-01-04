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

if 'trades' not in st.session_state:
    st.session_state.trades = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.trades = data.get("trades", [])
        except: pass

if 'deposit' not in st.session_state: st.session_state.deposit = 1000.0
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'timeframe' not in st.session_state: st.session_state.timeframe = "15m"
if 'last_price' not in st.session_state: st.session_state.last_price = 0.0

def save_data():
    try:
        data = {"trades": st.session_state.trades, "deposit": st.session_state.deposit}
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# 3. Улучшенная функция получения данных (Binance Spot & Futures)
def get_crypto_data(ticker, tf, market_type):
    tf_map = {"5m": ("histominute", 5), "15m": ("histominute", 15), "1h": ("histohour", 1), "4h": ("histohour", 4), "1d": ("histoday", 1)}
    endpoint, aggregate = tf_map.get(tf, ("histominute", 15))
    
    # Исправленное название биржи для фьючерсов
    exchange = "Binance" if market_type == "SPOT" else "BinanceFutures"
    
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={ticker}&tsym=USDT&limit=500&aggregate={aggregate}&e={exchange}"
        res = requests.get(url, timeout=5).json()
        
        if res.get('Response') == 'Success' and 'Data' in res.get('Data', {}):
            df = pd.DataFrame(res['Data']['Data'])
            if not df.empty:
                df['time'] = pd.to_datetime(df['time'], unit='s')
                st.session_state.last_price = float(df['close'].iloc[-1])
                return df
        return None
    except:
        return None

# 4. Интерфейс
if not st.session_state.logged_in:
    st.title("🔐 Helzin Terminal")
    if st.button("Войти в систему", use_container_width=True): 
        st.session_state.logged_in = True
        st.rerun()
else:
    # Сайдбар с вводом
    with st.sidebar:
        st.header(f"👤 admin")
        st.session_state.deposit = st.number_input("Депозит ($)", value=float(st.session_state.deposit))
        st.divider()
        
        st.subheader("➕ Новая сделка")
        # Используем форму, чтобы не было ошибок при наборе
        with st.form("trade_form", clear_on_submit=False):
            side = st.radio("Направление", ["LONG", "SHORT"], horizontal=True)
            coin_in = st.text_input("Монета", value="BTC").upper()
            
            # Поле ввода подхватывает последнюю известную цену
            ent = st.text_input("Цена входа", value=str(st.session_state.last_price))
            amt = st.text_input("Кол-во монет (напр. 0.1)")
            sl = st.text_input("Стоп-лосс")
            tp = st.text_input("Тейк-профит")
            
            if st.form_submit_button("ОТКРЫТЬ ПОЗИЦИЮ", use_container_width=True):
                try:
                    e = float(ent.replace(',', '.').strip())
                    a = float(amt.replace(',', '.').strip())
                    s = float(sl.replace(',', '.').strip())
                    tk = float(tp.replace(',', '.').strip())
                    
                    st.session_state.trades.append({
                        "id": datetime.now().timestamp(),
                        "Время": datetime.now().strftime("%H:%M:%S"),
                        "Тип": side, "Монета": coin_in, "Кол-во": a, "Вход": e, "Stop": s, "Тейк": tk,
                        "profit_num": abs(tk-e)*a, "loss_num": abs(e-s)*a, "Статус": "OPEN"
                    })
                    save_data(); st.success("Позиция открыта!"); st.rerun()
                except:
                    st.error("❌ Ошибка ввода! Используйте цифры и точки.")

        if st.button("Выйти"): 
            st.session_state.logged_in = False
            st.rerun()

    t1, t2 = st.tabs(["🕯 Торговля", "📑 Журнал"])
    
    with t1:
        # Селекторы сверху
        c1, c2, c3 = st.columns([1, 1, 3])
        active_coin = c1.text_input("Тикер", "BTC", key="main_t").upper()
        market_type = c2.selectbox("Рынок", ["SPOT", "FUTURES"], key="m_type")
        
        with c3:
            st.write("Таймфрейм")
            ts = st.columns(5)
            for i, f in enumerate(["5m", "15m", "1h", "4h", "1d"]):
                if ts[i].button(f, key=f"tf_{f}", type="primary" if st.session_state.timeframe == f else "secondary"):
                    st.session_state.timeframe = f; st.rerun()

        # Получаем данные
        df = get_crypto_data(active_coin, st.session_state.timeframe, market_type)

        # Карточки статистики
        closed = [t for t in st.session_state.trades if "PROFIT" in t['Статус'] or "LOSS" in t['Статус']]
        total_pnl = sum([(t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num']) for t in closed])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Текущая цена", f"${st.session_state.last_price:,.2f}")
        m2.metric("Общий P/L", f"${total_pnl:,.2f}")
        m3.metric("Активных сделок", len([t for t in st.session_state.trades if t['Статус'] == "OPEN"]))

        if df is not None:
            fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            
            # Линии сделок (рисуем только если монета совпадает)
            for tr in st.session_state.trades:
                if tr['Статус'] == "OPEN" and tr['Монета'] == active_coin:
                    fig.add_hline(y=tr['Вход'], line_color="white", annotation_text="Вход")
                    fig.add_hline(y=tr['Тейк'], line_dash="dash", line_color="#00ff88", annotation_text="TP")
                    fig.add_hline(y=tr['Stop'], line_dash="dash", line_color="#ff4b4b", annotation_text="SL")

            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10),
                              yaxis=dict(side="right", autorange=True, fixedrange=False), xaxis=dict(fixedrange=False))
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
        else:
            st.warning(f"⚠️ Данные для {active_coin} на {market_type} не найдены. Попробуйте сменить тикер или рынок.")

        st.divider()
        st.subheader("📈 Кривая доходности")
        if closed:
            bal = [st.session_state.deposit]
            curr = st.session_state.deposit
            for t in sorted(closed, key=lambda x: x['id']):
                curr += (t['profit_num'] if "PROFIT" in t['Статус'] else -t['loss_num'])
                bal.append(curr)
            st.line_chart(bal)
        else:
            st.info("Нет закрытых сделок для построения графика.")

    with t2:
        if not st.session_state.trades:
            st.write("Журнал пуст.")
        else:
            h = st.columns([1, 1, 1, 1, 1, 0.5])
            for i, n in enumerate(["Время", "Монета", "Вход", "Кол-во", "Статус", "Удалить"]): h[i].write(f"**{n}**")
            for tr in reversed(st.session_state.trades):
                r = st.columns([1, 1, 1, 1, 1, 0.5])
                r[0].write(tr['Время'])
                r[1].write(tr['Монета'])
                r[2].write(str(tr['Вход']))
                r[3].write(str(tr['Кол-во']))
                clr = "green" if "PROFIT" in tr['Статус'] else "red" if "LOSS" in tr['Статус'] else "white"
                r[4].markdown(f":{clr}[{tr['Статус']}]")
                if r[5].button("🗑️", key=f"del_{tr['id']}"):
                    st.session_state.trades.remove(tr); save_data(); st.rerun()
            
            if st.button("🔥 ОЧИСТИТЬ ВСЮ ИСТОРИЮ", use_container_width=True):
                st.session_state.trades = []
                save_data(); st.rerun()
                
