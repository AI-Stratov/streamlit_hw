import os
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context

import numpy as np
import pandas as pd
from joblib import Parallel, delayed


def analyze_city(city_data):
    """Анализ данных для одного конкретного города."""
    city_data = city_data.sort_values('timestamp').copy()

    # 1. Скользящее среднее (30 дней)
    city_data['rolling_mean'] = city_data['temperature'].rolling(window=30).mean()

    # 2. Сезонные профили (среднее и std)
    city_data['is_anomaly'] = False
    for season in city_data['season'].unique():
        mask = city_data['season'] == season
        season_stats = city_data[mask]['temperature'].agg(['mean', 'std'])

        upper = season_stats['mean'] + 2 * season_stats['std']
        lower = season_stats['mean'] - 2 * season_stats['std']

        city_data.loc[mask, 'is_anomaly'] = (city_data.loc[mask, 'temperature'] > upper) | \
                                            (city_data.loc[mask, 'temperature'] < lower)

    # 3. Тренды (линейная регрессия)
    x = np.arange(len(city_data))
    y = city_data['temperature'].values
    slope, intercept = np.polyfit(x, y, 1)
    city_data['trend'] = x * slope + intercept

    return city_data


def run_sequential(cities):
    return pd.concat([analyze_city(city) for city in cities])

def run_multiprocessing(cities):
    cpus = os.cpu_count() or 1
    workers = min(cpus, len(cities))

    with get_context("spawn").Pool(processes=workers) as pool:
        result = pool.map(analyze_city, cities)

    return pd.concat(result)

def run_threading(cities):
    workers = min(4, len(cities))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        result = list(executor.map(analyze_city, cities))
    return pd.concat(result)

def run_joblib(cities):
    # n_jobs=-1 использует все доступные ядра
    result = Parallel(n_jobs=-1)(delayed(analyze_city)(city) for city in cities)
    return pd.concat(result)


def parallel_analysis(df):
    cities = [group for _, group in df.groupby('city')]
    workers = min(4, len(cities))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        result_parts = list(executor.map(analyze_city, cities))

    return pd.concat(result_parts)