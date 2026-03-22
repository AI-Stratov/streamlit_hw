from typing import Optional

from pydantic import BaseModel


class WeatherMetrics(BaseModel):
    temp: float
    feels_like: float
    pressure: int
    humidity: int


class WeatherEntity(BaseModel):
    main: WeatherMetrics
    cod: int | str
    name: Optional[str] = None
    message: Optional[str] = None
