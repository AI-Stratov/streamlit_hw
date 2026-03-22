import asyncio
import os
import time
from datetime import datetime

import nest_asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_analysis import parallel_analysis, run_joblib, run_multiprocessing, run_sequential, run_threading
from src.exceptions import InvalidAPIKeyException, OpenWeatherException
from src.generate_data import month_to_season
from src.utils import EXPERIMENT_CONCLUSIONS
from src.weather_api import get_multiple_weather_async, get_multiple_weather_sync, get_weather_sync

# RuntimeError: This event loop is already running
nest_asyncio.apply()


@st.cache_data
def load_and_analyze_data(df):
    return parallel_analysis(df)


def main():
    st.set_page_config(page_title="Climate Monitor", layout="wide")
    st.title("Анализ температурных данных и мониторинг текущей температуры")

    st.sidebar.header("Настройки")
    uploaded_file = st.sidebar.file_uploader("Загрузите исторические данные", type="csv")
    api_key = st.sidebar.text_input("OpenWeatherMap API Key", type="password")

    if not uploaded_file:
        st.info("Пожалуйста, загрузите CSV файл с историческими данными для начала работы.")
        return

    df = pd.read_csv(uploaded_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    with st.expander("Эксперимент: Сравнение методов параллелизма"):
        cpu_count = os.cpu_count() or 1
        st.write(f"Доступно ядер CPU: **{cpu_count}**")
        if cpu_count == 1:
            st.warning(
                "Внимание: На 1 ядре параллельные методы будут медленнее последовательного из-за накладных расходов.")

        if st.button("Запустить тест"):
            cities_list = [group for _, group in df.groupby('city')]
            results = []
            with st.spinner("Проводим бенчмарки..."):
                for name, func in [("Последовательный", run_sequential),
                                   ("Multiprocessing (Pool)", run_multiprocessing),
                                   ("Threading (4 threads)", run_threading),
                                   ("Joblib (Parallel)", run_joblib)]:
                    t0 = time.perf_counter()
                    try:
                        _ = func(cities_list)
                        res = round(time.perf_counter() - t0, 4)
                    except Exception:
                        res = None
                    results.append({"Метод": name, "Время (сек)": res})

            res_df = pd.DataFrame(results)
            st.table(res_df)

            chart_df = res_df.dropna(subset=["Время (сек)"])
            if not chart_df.empty:
                st.bar_chart(chart_df.set_index("Метод"))
            else:
                st.warning("Все методы завершились с ошибкой - график недоступен.")

            st.info("**Вывод:**")
            st.write(EXPERIMENT_CONCLUSIONS)

    analyzed_df = load_and_analyze_data(df)
    city = st.selectbox("Выберите город для детального анализа", analyzed_df['city'].unique())
    city_data = analyzed_df[analyzed_df['city'] == city]

    st.subheader(f"Сезонные профили: {city}")
    season_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std', 'min', 'max']).reset_index()

    st.dataframe(
        season_stats.style.format({"mean": "{:.2f}", "std": "{:.2f}", "min": "{:.1f}", "max": "{:.1f}"}),
        use_container_width=True
    )

    season_stats['std_2'] = season_stats['std'] * 2
    fig_bar = px.bar(season_stats, x='season', y='mean', error_y='std_2',
                     title="Средняя температура по сезонам (± 2 std)",
                     color='season')
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader(f"История температур: {city}")
    fig_line = px.line(city_data, x='timestamp', y=['temperature', 'rolling_mean', 'trend'],
                       title=f"Временной ряд для {city} с выделением тренда и сглаживания",
                       color_discrete_map={"temperature": "lightblue", "rolling_mean": "orange", "trend": "red"})

    anom = city_data[city_data['is_anomaly']]
    fig_line.add_scatter(x=anom['timestamp'], y=anom['temperature'],
                         mode='markers', name='Аномалия', marker=dict(color='red', size=6))
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    if api_key:
        st.subheader("Мониторинг в реальном времени и тест API")

        all_cities = df['city'].unique().tolist()[:10]
        with st.expander("Эксперимент: Sync vs Async API"):
            if st.button("Запустить тест сети"):
                with st.spinner("Опрашиваем API..."):
                    _, t_sync = get_multiple_weather_sync(all_cities, api_key)
                    _, t_async = asyncio.run(get_multiple_weather_async(all_cities, api_key))
                    cn1, cn2 = st.columns(2)
                    cn1.metric("Синхронный опрос (for loop)", f"{t_sync:.2f} сек")
                    cn2.metric("Асинхронный опрос (asyncio)", f"{t_async:.2f} сек")
                    st.success(
                        "Вывод: Асинхронные запросы выполняются конкурентно, экономя время при сетевых вызовах (I/O).")

        try:
            weather = get_weather_sync(city, api_key)
            curr_temp = weather.main.temp

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
                st.error(f"Аномальная температура для сезона {current_season}!")
            else:
                st.success(f"Температура в пределах нормы для сезона {current_season}.")

        except InvalidAPIKeyException:
            st.error(
                '{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}')
        except OpenWeatherException as e:
            st.error(f"Ошибка API: {e.message}")
    else:
        st.warning("Введите API ключ для мониторинга текущей температуры.")


if __name__ == "__main__":
    main()
