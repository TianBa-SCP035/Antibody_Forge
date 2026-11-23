"""首页天气（北京）：先查 Open-Meteo，失败再查 weather-api.site；成功结果全站共用 30 分钟。"""

import logging
import threading
import time

import requests

logger = logging.getLogger(__name__)

_LATITUDE = 39.9042
_LONGITUDE = 116.4074
_TIMEOUT_SECONDS = 5
_CACHE_SECONDS = 30 * 60
# 正在查、刚查失败时，这么久以内的旧结果可以先顶上，再旧就报不可用。
_STALE_SECONDS = 60 * 60
# 外网不通时每次要等满超时，失败后这段时间内不再去查。
_RETRY_SECONDS = 60
# 前端按国标 HJ 633 由这些浓度算 AQI。
POLLUTANTS = ("pm2_5", "pm10", "sulphur_dioxide", "nitrogen_dioxide", "ozone", "carbon_monoxide")

_lock = threading.Lock()
_cached: tuple[float, dict] | None = None
_failed_at: float | None = None


class WeatherUnavailable(Exception):
    pass


def _get_json(url: str, params: dict) -> dict:
    response = requests.get(url, params=params, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def _air(url: str, params: dict) -> dict | None:
    """空气质量查不到不影响天气。"""
    try:
        current = _get_json(url, params).get("current") or {}
    except (requests.RequestException, ValueError):
        return None
    return {key: current[key] for key in POLLUTANTS if isinstance(current.get(key), (int, float))}


def _open_meteo() -> dict:
    point = {"latitude": _LATITUDE, "longitude": _LONGITUDE}
    current = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            **point,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "Asia/Shanghai",
        },
    ).get("current")
    if not current:
        raise ValueError("Open-Meteo 没有返回当前天气")
    return {
        "temp": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "air": _air("https://air-quality-api.open-meteo.com/v1/air-quality", {**point, "current": ",".join(POLLUTANTS)}),
    }


def _weather_api_site() -> dict:
    point = {"lat": _LATITUDE, "lon": _LONGITUDE}
    current = _get_json("https://weather-api.site/weather", point).get("current")
    if not current:
        raise ValueError("weather-api.site 没有返回当前天气")
    return {
        "temp": current.get("temperature"),
        "humidity": current.get("humidity"),
        "wind_speed": current.get("wind_speed"),
        "weather_code": current.get("condition_code"),
        "air": _air("https://weather-api.site/air-quality", point),
    }


def _fresh(max_age: float) -> dict | None:
    if _cached and time.monotonic() - _cached[0] < max_age:
        return _cached[1]
    return None


def _stale_or_raise(reason: str) -> dict:
    data = _fresh(_STALE_SECONDS)
    if data is None:
        raise WeatherUnavailable(reason)
    return data


def current_weather() -> dict:
    """同一时刻只有一个请求去外网查，其余请求不等它（接口共用线程池，排队会拖慢别的接口），先用旧结果或报不可用。"""
    global _cached, _failed_at
    data = _fresh(_CACHE_SECONDS)
    if data is not None:
        return data
    if not _lock.acquire(blocking=False):
        return _stale_or_raise("正在查询天气")
    try:
        data = _fresh(_CACHE_SECONDS)
        if data is not None:
            return data
        if _failed_at is not None and time.monotonic() - _failed_at < _RETRY_SECONDS:
            return _stale_or_raise("刚查询失败，稍后再查")
        errors = []
        for provider in (_open_meteo, _weather_api_site):
            try:
                data = provider()
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{provider.__name__}: {exc}")
                continue
            _cached = (time.monotonic(), data)
            _failed_at = None
            return data
        _failed_at = time.monotonic()
        logger.warning("首页天气查询失败：%s", "；".join(errors))
        return _stale_or_raise("；".join(errors))
    finally:
        _lock.release()
