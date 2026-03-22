import asyncio
import time

import aiohttp
import requests

from src.entities import WeatherEntity
from src.exceptions import InvalidAPIKeyException, CityNotFoundException, OpenWeatherException


def get_weather_sync(city: str, api_key: str) -> WeatherEntity:
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        try:
            cod = int(data.get("cod", 500))
        except (ValueError, TypeError):
            cod = 500

        if cod == 200:
            return WeatherEntity(**data)
        elif cod == 401:
            raise InvalidAPIKeyException(data.get("message", ""), cod=401)
        elif cod == 404:
            raise CityNotFoundException(data.get("message", ""), cod=404)
        else:
            raise OpenWeatherException(data.get("message", ""), cod=cod)
    except requests.RequestException as e:
        raise OpenWeatherException(f"Network error: {str(e)}")


async def fetch_weather_async(session: aiohttp.ClientSession, city: str, api_key: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    timeout = aiohttp.ClientTimeout(total=5)
    async with session.get(url, timeout=timeout) as resp:
        return await resp.json()


async def get_multiple_weather_async(cities: list[str], api_key: str):
    start_time = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [fetch_weather_async(session, city, api_key) for city in cities]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results, time.perf_counter() - start_time


def get_multiple_weather_sync(cities: list[str], api_key: str):
    start_time = time.perf_counter()
    results = []
    for city in cities:
        try:
            results.append(get_weather_sync(city, api_key))
        except Exception:
            results.append(None)
    return results, time.perf_counter() - start_time
