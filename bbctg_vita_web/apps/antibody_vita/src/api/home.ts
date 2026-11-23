import { requestClient, skipGlobalErrorHandler } from '#/api/request';

/** 后端查到的北京当前天气；air 为各污染物浓度（μg/m³），查不到时为 null。 */
export interface HomeWeather {
  air: null | Record<string, number>;
  humidity: null | number;
  temp: null | number;
  weather_code: null | number;
  wind_speed: null | number;
}

export function fetchHomeWeather() {
  return requestClient.get<HomeWeather>('/home/weather', skipGlobalErrorHandler);
}
