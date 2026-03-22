import asyncio
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_analysis import parallel_analysis, sequential_analysis
from src.generate_data import month_to_season
from src.weather_api import get_weather_sync, get_multiple_weather_sync, get_multiple_weather_async

st.set_page_config(page_title="Climate Monitor", layout="wide")

st.title("🌡️ Анализ температурных данных и мониторинг текущей температуры")


@st.cache_data
def load_and_analyze_data(df):
    return parallel_analysis(df)


st.sidebar.header("Настройки")
uploaded_file = st.sidebar.file_uploader("Загрузите исторические данные", type="csv")
api_key = st.sidebar.text_input("OpenWeatherMap API Key", type="password")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    with st.expander("🚀 Провести эксперимент: Последовательный vs Параллельный анализ (CPU)"):
        if st.button("Запустить тест CPU"):
            with st.spinner("Считаем..."):
                t0 = time.perf_counter()
                _ = sequential_analysis(df)
                t_seq = time.perf_counter() - t0

                t0 = time.perf_counter()
                _ = parallel_analysis(df)
                t_par = time.perf_counter() - t0

                col1, col2 = st.columns(2)
                col1.metric("Последовательно", f"{t_seq:.3f} сек")
                col2.metric("Параллельно (Pool)", f"{t_par:.3f} сек")

                if t_par > t_seq:
                    st.warning("⚠️ Последовательный метод оказался быстрее параллельного.")
                    st.info(
                        "**Аналитический вывод:** Несмотря на то, что серверы Streamlit Cloud работают на Linux "
                        "(где процессы создаются быстро через `fork`, в отличие от Windows), накладные расходы на "
                        "инициализацию `multiprocessing.Pool` всё равно превышают выгоду от распараллеливания. "
                        "Причина кроется в размере данных: ~55 000 строк - слишком малый объем. Библиотека Pandas "
                        "оптимизирована на C и обрабатывает его в одном потоке за доли секунды. Параллельность "
                        "даст реальный прирост скорости только на 'тяжелых' датасетах (от сотен тысяч строк)."
                    )
                else:
                    st.success("✅ Параллельный метод оказался быстрее!")
                    st.info(
                        "**Аналитический вывод:** Объем данных оказался достаточным, чтобы выигрыш от распределения "
                        "задач по ядрам процессора перекрыл накладные расходы на создание процессов в операционной системе."
                    )

    analyzed_df = load_and_analyze_data(df)

    city = st.selectbox("Выберите город для детального анализа", analyzed_df['city'].unique())
    city_data = analyzed_df[analyzed_df['city'] == city]

    st.subheader(f"📊 Сезонные профили: {city}")
    season_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std', 'min', 'max']).reset_index()

    col_stat1, col_stat2 = st.columns([1, 2])
    with col_stat1:
        st.dataframe(season_stats.style.format({"mean": "{:.2f}", "std": "{:.2f}", "min": "{:.1f}", "max": "{:.1f}"}))
    with col_stat2:
        season_stats['std_2'] = season_stats['std'] * 2

        fig_bar = px.bar(season_stats, x='season', y='mean', error_y='std_2',
                         title="Средняя температура по сезонам (± 2 std)",
                         color='season')
        st.plotly_chart(fig_bar, width='stretch')

    st.subheader(f"📈 История температур: {city}")
    fig = px.line(city_data, x='timestamp', y=['temperature', 'rolling_mean', 'trend'],
                  title=f"Временной ряд для {city} с выделением тренда и сглаживания",
                  color_discrete_map={"temperature": "lightblue", "rolling_mean": "orange", "trend": "red"})

    anomalies = city_data[city_data['is_anomaly']]
    fig.add_scatter(x=anomalies['timestamp'], y=anomalies['temperature'],
                    mode='markers', name='Аномалия', marker=dict(color='red', size=6))
    st.plotly_chart(fig, width='stretch')

    st.divider()
    if api_key:
        st.subheader("🌍 Мониторинг в реальном времени и тест API")

        all_cities = df['city'].unique().tolist()
        with st.expander("⚡ Провести эксперимент: Sync vs Async API (Network)"):
            if st.button("Запустить тест сети"):
                with st.spinner("Опрашиваем API для всех городов..."):
                    _, t_sync = get_multiple_weather_sync(all_cities, api_key)
                    _, t_async = asyncio.run(get_multiple_weather_async(all_cities, api_key))

                    col_net1, col_net2 = st.columns(2)
                    col_net1.metric("Синхронный опрос (for loop)", f"{t_sync:.2f} сек")
                    col_net2.metric("Асинхронный опрос (asyncio)", f"{t_async:.2f} сек")
                    st.success(
                        "Вывод: Асинхронные запросы выполняются конкурентно, экономя время при сетевых вызовах (I/O).")

        sync_data = get_weather_sync(city, api_key)
        cod = str(sync_data.get("cod", ""))

        if cod == "200":
            curr_temp = sync_data['main']['temp']

            current_month = datetime.now().month
            current_season = month_to_season[current_month]

            stats = city_data[city_data['season'] == current_season]['temperature'].agg(['mean', 'std'])
            mean_temp = stats['mean']
            std_temp = stats['std']

            is_anomaly = curr_temp > (mean_temp + 2 * std_temp) or curr_temp < (mean_temp - 2 * std_temp)

            res_col1, res_col2 = st.columns(2)
            res_col1.metric("Текущая температура", f"{curr_temp}°C")
            res_col2.metric("Текущий сезон (норма)", f"{mean_temp:.1f} °C (±{2 * std_temp:.1f})", current_season)

            if is_anomaly:
                st.error(f"🚨 Аномальная температура для сезона {current_season}!")
            else:
                st.success(f"✅ Температура в пределах нормы для сезона {current_season}.")

        elif cod == "401":
            st.error(
                '{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}')
        else:
            st.error(f"Ошибка API: {sync_data.get('message', 'Неизвестная ошибка')}")
    else:
        st.warning("Введите API ключ для мониторинга текущей температуры.")
else:
    st.info(
        "Пожалуйста, загрузите CSV файл с историческими данными (temperature_data.csv) в боковой панели для начала работы.")
