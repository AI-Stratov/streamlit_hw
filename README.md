# Анализ температурных данных и мониторинг текущей температуры через OpenWeatherMap API

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)
![OpenWeatherMap](https://img.shields.io/badge/OpenWeather-EB6E4B?style=for-the-badge&logo=openweathermap&logoColor=white)


## Описание
Интерактивное веб-приложение для анализа исторических температурных данных и мониторинга текущей погоды в реальном времени. Приложение вычисляет скользящие средние, находит температурные аномалии, строит сезонные профили и сравнивает текущую погоду с исторической нормой.

**[ОТКРЫТЬ ПРИЛОЖЕНИЕ В STREAMLIT CLOUD](https://apphw-duwdvhgsx4jvobmydjz8vk.streamlit.app/)**

*(Для работы приложения потребуется загрузить файл с историческими данными `temperature_data.csv` и ввести API-ключ OpenWeatherMap)*

---

## Результаты экспериментов (Синхронность vs Асинхронность & Распараллеливание)

В рамках проекта были проведены исследования производительности для разных типов задач:

### 1. Вычислительные задачи (CPU-bound): Анализ данных
Сравнивался последовательный анализ Pandas и распараллеленный с помощью `multiprocessing.Pool`.
* **Вывод:** На использованном объеме данных (~55 000 строк) последовательный метод оказался быстрее параллельного. Библиотека Pandas, оптимизированная на C, обрабатывает этот объем за доли секунды. Накладные расходы (overhead) на создание новых процессов операционной системы превышают выгоду от распараллеливания. Использование `multiprocessing` целесообразно только на "тяжелых" датасетах, исчисляемых миллионами строк.

### 2. Сетевые запросы (I/O-bound): Опрос OpenWeatherMap API
Сравнивался последовательный опрос городов через `requests` и асинхронный через `aiohttp` / `asyncio`.
* **Вывод:** Асинхронный подход показал колоссальное преимущество (работает в десятки раз быстрее). При синхронном подходе программа простаивает, ожидая ответа от сервера для каждого города. Асинхронность позволяет отправлять запросы конкурентно (почти одновременно), в результате чего общее время выполнения равно времени самого долгого запроса, а не сумме всех.