import type { Ref } from 'vue';
import { onMounted, reactive, ref, watch } from 'vue';

import { preferences } from '@vben/preferences';

import { $t } from '#/locales';

const BEIJING_LAT = 39.9042;
const BEIJING_LON = 116.4074;
const QWEATHER_LOCATION = '101010100';

const WMO_CODES = [
  0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77,
  80, 81, 82, 85, 86, 95, 96, 99,
] as const;

function isNightHour() {
  const h = new Date().getHours();
  return h < 6 || h >= 19;
}

export function qweatherIconToWmo(icon: string | number): number {
  const n = Number(icon);
  if (Number.isNaN(n)) return 3;
  if ([100, 150].includes(n)) return 0;
  if ([102, 152].includes(n)) return 1;
  if ([101, 151, 103, 153].includes(n)) return 2;
  if ([104, 154].includes(n)) return 3;
  if ([500, 501, 509, 510, 514, 515, 502, 511, 512, 513, 504, 503, 507, 508].includes(n)) {
    return 45;
  }
  if ([300, 350].includes(n)) return 80;
  if ([301, 351].includes(n)) return 81;
  if ([302, 303].includes(n)) return 95;
  if (n === 304) return 96;
  if ([305, 309, 314].includes(n)) return 61;
  if ([306, 315].includes(n)) return 63;
  if ([307, 308, 310, 311, 312, 316, 317, 318, 399].includes(n)) return 65;
  if (n === 313) return 66;
  if ([400, 408, 456, 404, 405].includes(n)) return 71;
  if ([401, 409].includes(n)) return 73;
  if ([402, 410].includes(n)) return 75;
  if (n === 403) return 77;
  if ([406, 407, 457].includes(n)) return 85;
  return 3;
}

export function wmoWeatherIcon(code: number): string {
  const night = isNightHour();

  if (code === 0) return night ? 'meteocons:clear-night-fill' : 'meteocons:clear-day-fill';
  if (code === 1) {
    return night ? 'meteocons:partly-cloudy-night-fill' : 'meteocons:partly-cloudy-day-fill';
  }
  if (code === 2) {
    return night ? 'meteocons:partly-cloudy-night-fill' : 'meteocons:partly-cloudy-day-fill';
  }
  if (code === 3) return 'meteocons:overcast-fill';
  if (code === 45 || code === 48) return 'meteocons:fog-fill';
  if (code >= 51 && code <= 55) return 'meteocons:drizzle-fill';
  if (code === 56 || code === 57 || code === 66 || code === 67) {
    return 'meteocons:sleet-fill';
  }
  if (code === 61 || code === 80) return 'meteocons:rain-fill';
  if (code === 63 || code === 81) return 'meteocons:rain-fill';
  if (code === 65 || code === 82) return 'meteocons:rain-heavy-fill';
  if (code === 71 || code === 85) return 'meteocons:snow-fill';
  if (code === 73 || code === 86) return 'meteocons:snow-fill';
  if (code === 75) return 'meteocons:snow-fill';
  if (code === 77) return 'meteocons:hail-fill';
  if (code === 95) return 'meteocons:thunderstorms-fill';
  if (code === 96 || code === 99) return 'meteocons:thunderstorms-extreme-fill';
  return night ? 'meteocons:partly-cloudy-night-fill' : 'meteocons:partly-cloudy-day-fill';
}

function wmoLabel(code: number): string {
  if (WMO_CODES.includes(code as (typeof WMO_CODES)[number])) {
    return $t(`page.home.weatherWmo.${code}`);
  }
  return $t('page.home.weatherUnknown');
}

function chinaAqiLevel(aqi: number | null): string | null {
  if (aqi === null || Number.isNaN(aqi)) return null;
  if (aqi <= 50) return $t('page.home.aqiGood');
  if (aqi <= 100) return $t('page.home.aqiFair');
  if (aqi <= 150) return $t('page.home.aqiModerate');
  if (aqi <= 200) return $t('page.home.aqiPoor');
  return $t('page.home.aqiVeryPoor');
}

function europeanAqiLevel(aqi: number | null): string | null {
  if (aqi === null || Number.isNaN(aqi)) return null;
  if (aqi <= 20) return $t('page.home.aqiGood');
  if (aqi <= 40) return $t('page.home.aqiFair');
  if (aqi <= 60) return $t('page.home.aqiModerate');
  if (aqi <= 80) return $t('page.home.aqiPoor');
  return $t('page.home.aqiVeryPoor');
}

export interface HomeWeatherState {
  aqi: number | null;
  aqiLevel: string | null;
  humidity: number | null;
  icon: string;
  label: string;
  loading: boolean;
  temp: number | null;
  windSpeed: number | null;
}

function parseIntField(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : Math.round(n);
}

function applyWeatherCode(
  weather: HomeWeatherState,
  lastWeatherCode: Ref<number | null>,
  lastAqi: Ref<number | null>,
  code: number,
  aqi: number | null,
  aqiLevelFn: (v: number | null) => string | null,
) {
  lastWeatherCode.value = code;
  lastAqi.value = aqi;
  weather.icon = wmoWeatherIcon(code);
  weather.aqi = aqi;
  weather.label = wmoLabel(code);
  weather.aqiLevel = aqiLevelFn(aqi);
}

function unavailableState(): Partial<HomeWeatherState> {
  return {
    label: $t('page.home.weatherUnavailable'),
    icon: 'meteocons:cloudy-fill',
    temp: null,
    humidity: null,
    windSpeed: null,
    aqi: null,
    aqiLevel: null,
  };
}

async function loadFromQWeather(
  weather: HomeWeatherState,
  lastWeatherCode: Ref<number | null>,
  lastAqi: Ref<number | null>,
  key: string,
) {
  const host =
    (import.meta.env.VITE_QWEATHER_API_HOST as string)?.trim() ||
    'https://devapi.qweather.com';
  const base = host.replace(/\/$/, '');
  const qs = `location=${QWEATHER_LOCATION}&key=${encodeURIComponent(key)}`;

  const weatherRes = await fetch(`${base}/v7/weather/now?${qs}`);
  if (!weatherRes.ok) throw new Error('QWeather now failed');
  const weatherJson = (await weatherRes.json()) as {
    code?: string;
    now?: { temp?: string; humidity?: string; windSpeed?: string; icon?: string };
  };
  if (weatherJson.code !== '200' || !weatherJson.now) {
    throw new Error(`QWeather code=${weatherJson.code}`);
  }

  const now = weatherJson.now;
  const code = qweatherIconToWmo(now.icon ?? '');
  weather.temp = parseIntField(now.temp);
  weather.humidity = parseIntField(now.humidity);
  weather.windSpeed = parseIntField(now.windSpeed);

  let aqi: number | null = null;
  try {
    const airRes = await fetch(`${base}/v7/air/now?${qs}`);
    if (airRes.ok) {
      const airJson = (await airRes.json()) as {
        code?: string;
        now?: { aqi?: string };
      };
      if (airJson.code === '200' && airJson.now) {
        aqi = parseIntField(airJson.now.aqi);
      }
    }
  } catch {
    /* 空气质量可选 */
  }

  applyWeatherCode(weather, lastWeatherCode, lastAqi, code, aqi, chinaAqiLevel);
}

async function loadFromOpenMeteo(
  weather: HomeWeatherState,
  lastWeatherCode: Ref<number | null>,
  lastAqi: Ref<number | null>,
) {
  const forecastUrl = new URL('https://api.open-meteo.com/v1/forecast');
  forecastUrl.searchParams.set('latitude', String(BEIJING_LAT));
  forecastUrl.searchParams.set('longitude', String(BEIJING_LON));
  forecastUrl.searchParams.set(
    'current',
    'temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code',
  );
  forecastUrl.searchParams.set('timezone', 'Asia/Shanghai');

  const aqUrl = new URL('https://air-quality-api.open-meteo.com/v1/air-quality');
  aqUrl.searchParams.set('latitude', String(BEIJING_LAT));
  aqUrl.searchParams.set('longitude', String(BEIJING_LON));
  aqUrl.searchParams.set('current', 'european_aqi');

  const [forecastRes, aqRes] = await Promise.all([
    fetch(forecastUrl.toString()),
    fetch(aqUrl.toString()).catch(() => null),
  ]);

  const forecastJson = (await forecastRes.json()) as {
    current?: {
      temperature_2m?: number;
      relative_humidity_2m?: number;
      wind_speed_10m?: number;
      weather_code?: number;
    };
  };

  const current = forecastJson.current;
  if (!current) throw new Error('Open-Meteo empty');

  const code = current.weather_code ?? 3;
  weather.temp =
    current.temperature_2m !== undefined
      ? Math.round(current.temperature_2m)
      : null;
  weather.humidity =
    current.relative_humidity_2m !== undefined
      ? Math.round(current.relative_humidity_2m)
      : null;
  weather.windSpeed =
    current.wind_speed_10m !== undefined
      ? Math.round(current.wind_speed_10m)
      : null;

  let aqi: number | null = null;
  if (aqRes?.ok) {
    const aqJson = (await aqRes.json()) as {
      current?: { european_aqi?: number };
    };
    if (aqJson.current?.european_aqi !== undefined) {
      aqi = Math.round(aqJson.current.european_aqi);
    }
  }

  applyWeatherCode(weather, lastWeatherCode, lastAqi, code, aqi, europeanAqiLevel);
}

export function useHomeWeather() {
  const lastWeatherCode = ref<number | null>(null);
  const lastAqi = ref<number | null>(null);
  const aqiLevelFn = ref<(v: number | null) => string | null>(chinaAqiLevel);

  const weather = reactive<HomeWeatherState>({
    aqi: null,
    aqiLevel: null,
    humidity: null,
    icon: 'meteocons:cloudy-fill',
    label: $t('page.home.weatherLoading'),
    loading: true,
    temp: null,
    windSpeed: null,
  });

  function applyLocalizedLabels() {
    if (weather.loading) {
      weather.label = $t('page.home.weatherLoading');
      return;
    }
    if (lastWeatherCode.value === null) {
      weather.label = $t('page.home.weatherUnavailable');
      return;
    }
    weather.label = wmoLabel(lastWeatherCode.value);
    weather.aqiLevel = aqiLevelFn.value(lastAqi.value);
  }

  async function loadWeather() {
    weather.loading = true;
    weather.label = $t('page.home.weatherLoading');

    const qKey = (import.meta.env.VITE_QWEATHER_API_KEY as string | undefined)?.trim();

    try {
      if (qKey) {
        await loadFromQWeather(weather, lastWeatherCode, lastAqi, qKey);
        aqiLevelFn.value = chinaAqiLevel;
      } else {
        await loadFromOpenMeteo(weather, lastWeatherCode, lastAqi);
        aqiLevelFn.value = europeanAqiLevel;
      }
    } catch {
      if (qKey) {
        try {
          await loadFromOpenMeteo(weather, lastWeatherCode, lastAqi);
          aqiLevelFn.value = europeanAqiLevel;
        } catch {
          lastWeatherCode.value = null;
          lastAqi.value = null;
          Object.assign(weather, unavailableState());
        }
      } else {
        lastWeatherCode.value = null;
        lastAqi.value = null;
        Object.assign(weather, unavailableState());
      }
    } finally {
      weather.loading = false;
      if (lastWeatherCode.value !== null) {
        applyLocalizedLabels();
      }
    }
  }

  watch(
    () => preferences.app.locale,
    () => {
      if (!weather.loading) {
        applyLocalizedLabels();
      }
    },
  );

  onMounted(() => {
    void loadWeather();
  });

  return { weather };
}
