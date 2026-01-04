# --- ВНУТРИ tab1 (Блок кнопок ТФ) ---
with c3:
    st.write("Таймфрейм")
    bc = st.columns(5)
    tfs = ["5m", "15m", "1h", "4h", "1d"]
    for i, f in enumerate(tfs):
        # Подсветка кнопки: если ТФ выбран — тип primary (синий), иначе secondary
        is_active = (st.session_state.timeframe == f)
        if bc[i].button(f, key=f"tf_btn_{f}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
            st.session_state.timeframe = f
            st.rerun()

# --- ВНУТРИ live_chart_section (Настройки осей) ---
fig.update_layout(
    template="plotly_dark", 
    height=600, 
    xaxis_rangeslider_visible=False, 
    margin=dict(l=10, r=10, t=10, b=10),
    dragmode='pan',
    hovermode='x unified',
    yaxis=dict(
        side="right", 
        fixedrange=False, # Разрешает растягивать
        autorange=True    # Автоподбор под свечи
    ),
    xaxis=dict(
        fixedrange=False, # Разрешает сжимать время
        type='date'
    )
)

# Передаем настройки взаимодействия
st.plotly_chart(
    fig, 
    use_container_width=True, 
    config={
        'scrollZoom': True,      # Зум колесиком
        'displayModeBar': True,  # Показать инструменты
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'], # Убираем лишнее
        'doubleClick': 'reset+autosize' # Двойной клик сбросит всё в норму
    }
)
