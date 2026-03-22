
from pydantic import BaseModel


class WeatherMetrics(BaseModel):
    temp: float
    feels_like: float
    pressure: int
    humidity: int


class WeatherEntity(BaseModel):
    main: WeatherMetrics
    cod: int | str
    name: str | None = None
    message: str | None = None
