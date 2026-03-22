class OpenWeatherException(Exception):
    def __init__(self, message: str, cod: int = 500):
        self.message = message
        self.cod = cod
        super().__init__(self.message)


class InvalidAPIKeyException(OpenWeatherException):
    pass


class CityNotFoundException(OpenWeatherException):
    pass
