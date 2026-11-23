"""首页天气：主备接口切换、全站缓存、空气质量缺失、查询中与失败时不排队。"""

import json
import time
import unittest
from unittest.mock import patch

import requests
from requests import Response

from integrations import weather


def _response(payload, status=200):
    response = Response()
    response.status_code = status
    response._content = json.dumps(payload).encode()
    return response


OPEN_METEO = {"current": {"temperature_2m": 6.4, "relative_humidity_2m": 41, "wind_speed_10m": 9.8, "weather_code": 2}}
SITE = {"current": {"temperature": 7.1, "humidity": 38, "wind_speed": 11.2, "condition_code": 3}}
AIR = {"current": {"pm2_5": 30.5, "pm10": 61, "ozone": None}}


class WeatherTests(unittest.TestCase):
    def setUp(self):
        weather._cached = None
        weather._failed_at = None
        self.calls = []

    def fake_get(self, routes):
        def get(url, params=None, timeout=None):
            self.calls.append(url)
            result = routes[url]
            if isinstance(result, Exception):
                raise result
            return _response(result)
        return get

    def test_open_meteo_first_and_cached_for_everyone(self):
        routes = {
            "https://api.open-meteo.com/v1/forecast": OPEN_METEO,
            "https://air-quality-api.open-meteo.com/v1/air-quality": AIR,
        }
        with patch.object(weather.requests, "get", side_effect=self.fake_get(routes)):
            first = weather.current_weather()
            second = weather.current_weather()
        self.assertEqual(first, {
            "temp": 6.4, "humidity": 41, "wind_speed": 9.8, "weather_code": 2,
            "air": {"pm2_5": 30.5, "pm10": 61},
        })
        self.assertIs(second, first)
        self.assertEqual(len(self.calls), 2)

    def test_falls_back_to_weather_api_site(self):
        routes = {
            "https://api.open-meteo.com/v1/forecast": requests.ConnectionError("断网"),
            "https://weather-api.site/weather": SITE,
            "https://weather-api.site/air-quality": requests.Timeout("超时"),
        }
        with patch.object(weather.requests, "get", side_effect=self.fake_get(routes)):
            data = weather.current_weather()
        self.assertEqual(data, {"temp": 7.1, "humidity": 38, "wind_speed": 11.2, "weather_code": 3, "air": None})

    def test_all_failed_raises_and_is_not_cached(self):
        routes = {
            "https://api.open-meteo.com/v1/forecast": {"current": None},
            "https://weather-api.site/weather": requests.ConnectionError("断网"),
        }
        with patch.object(weather.requests, "get", side_effect=self.fake_get(routes)):
            with self.assertRaises(weather.WeatherUnavailable):
                weather.current_weather()
            with self.assertRaises(weather.WeatherUnavailable):
                weather.current_weather()
        self.assertIsNone(weather._cached)
        self.assertEqual(len(self.calls), 2)

    def test_does_not_wait_while_another_request_is_fetching(self):
        old = {"temp": 5}
        self.assertTrue(weather._lock.acquire(blocking=False))
        try:
            with patch.object(weather.requests, "get", side_effect=AssertionError("不应访问外网")):
                weather._cached = (time.monotonic() - 40 * 60, old)
                self.assertIs(weather.current_weather(), old)
                weather._cached = (time.monotonic() - 2 * 60 * 60, old)
                with self.assertRaises(weather.WeatherUnavailable):
                    weather.current_weather()
        finally:
            weather._lock.release()

    def test_all_failed_falls_back_to_recent_result(self):
        old = {"temp": 5}
        weather._cached = (time.monotonic() - 40 * 60, old)
        routes = {
            "https://api.open-meteo.com/v1/forecast": requests.Timeout("超时"),
            "https://weather-api.site/weather": requests.Timeout("超时"),
        }
        with patch.object(weather.requests, "get", side_effect=self.fake_get(routes)):
            self.assertIs(weather.current_weather(), old)
            self.assertIs(weather.current_weather(), old)
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()
