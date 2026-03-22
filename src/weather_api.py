import asyncio
import time

import aiohttp
import requests


def get_weather_sync(city, api_key):
    """Синхронный запрос для одного города."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except Exception as e:
        return {"cod": "error", "message": str(e)}


def get_multiple_weather_sync(cities, api_key):
    """Синхронный запрос для списка городов (для эксперимента)."""
    start = time.perf_counter()
    results = [get_weather_sync(city, api_key) for city in cities]
    return results, time.perf_counter() - start


async def get_weather_async(session, city, api_key):
    """Асинхронный запрос для одного города."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        async with session.get(url, timeout=5) as response:
            return await response.json()
    except Exception as e:
        return {"cod": "error", "message": str(e)}


async def get_multiple_weather_async(cities, api_key):
    """Асинхронный запрос для списка городов (для эксперимента)."""
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        tasks = [get_weather_async(session, city, api_key) for city in cities]
        results = await asyncio.gather(*tasks)
    return results, time.perf_counter() - start
