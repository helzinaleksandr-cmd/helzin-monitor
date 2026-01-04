# НАСТРОЙКИ ДЛЯ ГИБКОГО МАСШТАБА
        fig.update_layout(
            template="plotly_dark", 
            height=600, 
            xaxis_rangeslider_visible=False, 
            margin=dict(l=10, r=10, t=10, b=10),
            dragmode='pan', # Режим "ладошка" для перемещения
            hovermode='x unified',
            yaxis=dict(
                side="right", 
                fixedrange=False, # ЭТО ВАЖНО: разрешает зум по вертикали
                autorange=True,
            ),
            xaxis=dict(
                fixedrange=False  # ЭТО ВАЖНО: разрешает зум по горизонтали
            )
        )
        
        # КЛЮЧЕВОЙ МОМЕНТ: Добавляем config с 'scrollZoom' и 'modeBar'
        st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={
                'scrollZoom': True,        # Зум колесиком
                'displayModeBar': True,    # Показать панель инструментов сверху
                'modeBarButtonsToAdd': [
                    'zoomIn2d', 'zoomOut2d', 'resetScale2d'
                ]
            }
        )
