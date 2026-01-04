import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Helzin Terminal Pro", layout="wide")

if 'trades' not in st.session_state: st.session_state.trades = []
if 'balance' not in st.session_state: st.session_state.balance = 1000.0

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def convert_df(trades):
    # Превращаем список сделок в чистую таблицу для Excel
    if not trades: return None
    df = pd.DataFrame(trades)
    # Убираем лишние колонки (объекты картинок), чтобы Excel не ругался
    cols_to_save = [c for c in df.columns if c not in ['img_entry', 'img_exit', 'id']]
    return df[cols_to_save].to_csv(index=False).encode('utf-8-sig')

# --- САЙДБАР ---
with st.sidebar:
    st.title("👤 Helzin Admin")
    st.session_state.balance = st.number_input("Нач. Депозит ($)", value=float(st.session_state.balance))
    st.divider()
    
    # Кнопка экспорта в Excel
    st.subheader("📤 Экспорт данных")
    csv_data = convert_df(st.session_state.trades)
    if csv_data:
        st.download_button(
            label="СКАЧАТЬ ОТЧЕТ EXCEL",
            data=csv_data,
            file_name=f"trading_report_{datetime.now().strftime('%d_%m')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.caption("Сделок пока нет для экспорта")

# --- ДВИЖОК ТЕРМИНАЛА (КРАТКО) ---
@st.fragment(run_every=5)
def terminal_engine():
    # ... (здесь остается весь код логики цен, который мы писали ранее) ...
    
    # Считаем статистику для "Поделиться"
    closed = [t for t in st.session_state.trades if t['final_pnl'] is not None]
    total_trades = len(closed)
    wins = len([t for t in closed if t['final_pnl'] > 0])
    losses = len([t for t in closed if t['final_pnl'] <= 0])
    winrate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum([t['final_pnl'] for t in closed])
    
    t_trade, t_journal, t_stats = st.tabs(["🕯 ТОРГОВЛЯ", "📓 ЖУРНАЛ", "📊 МОЯ СТАТИСТИКА"])

    with t_trade:
        st.write("Торговый интерфейс...") # Тут твой график и PnL

    with t_journal:
        st.write("Журнал сделок...") # Тут твои Expanders

    with t_stats:
        st.subheader("🏆 Performance Report")
        
        # Красивые карточки для скриншота
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Win Rate", f"{winrate:.1f}%")
        s2.metric("Total Profit", f"${total_profit:.2f}")
        s3.metric("Trades", total_trades)
        s4.metric("Win/Loss", f"{wins} / {losses}")

        # Таблица достижений
        if total_trades > 0:
            st.divider()
            st.markdown("### 📈 Итоговая сводка")
            res_df = pd.DataFrame([
                {"Параметр": "Начальный баланс", "Значение": f"${st.session_state.balance}"},
                {"Параметр": "Текущий баланс", "Значение": f"${st.session_state.balance + total_profit:.2f}"},
                {"Параметр": "Профит-фактор", "Значение": "1.45 (Демо)"}, # Можно рассчитать реально
                {"Параметр": "Лучшая сделка", "Значение": f"${max([t['final_pnl'] for t in closed]):.2f}"}
            ])
            st.table(res_df)
            
            # Предложение сделать скрин
            st.info("💡 Совет: Используйте Win+Shift+S, чтобы сделать скриншот этой вкладки для отправки в Telegram!")
        else:
            st.info("Статистика будет доступна после закрытия первой сделки.")

terminal_engine()
