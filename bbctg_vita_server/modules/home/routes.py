from fastapi import APIRouter, Depends, HTTPException

from core.response import success
from integrations import weather
from modules.auth.dependencies import get_current_user

# 首页信息，登录即可读取。
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/weather")
def home_weather() -> dict:
    try:
        return success(weather.current_weather())
    except weather.WeatherUnavailable as exc:
        raise HTTPException(status_code=503, detail="天气服务暂不可用") from exc
