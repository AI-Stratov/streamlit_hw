from multiprocessing import Pool

import numpy as np
import pandas as pd


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


def parallel_analysis(df):
    """Распараллеливание по городам."""
    cities = [group for _, group in df.groupby('city')]
    with Pool() as pool:
        result_parts = pool.map(analyze_city, cities)
    return pd.concat(result_parts)


def sequential_analysis(df):
    """Последовательный анализ для сравнения."""
    return pd.concat([analyze_city(group) for _, group in df.groupby('city')])
