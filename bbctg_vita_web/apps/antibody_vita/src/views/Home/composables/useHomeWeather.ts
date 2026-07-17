import type { Ref } from 'vue';
import { onMounted, reactive, ref, watch } from 'vue';

import { preferences } from '@vben/preferences';

import { $t } from '#/locales';

const BEIJING_LAT = 39.9042;
const BEIJING_LON = 116.4074;
const WEATHER_CACHE_KEY = 'home-weather-beijing-v3';
const WEATHER_CACHE_TTL_MS = 30 * 60 * 1000;

const WMO_CODES = [
  0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77,
  80, 81, 82, 85, 86, 95, 96, 99,
] as const;

interface WeatherSnapshot {
  aqi: number | null;
  humidity: number | null;
  temp: number | null;
  weatherCode: number;
  windSpeed: number | null;
}

interface WeatherCachePayload extends WeatherSnapshot {
  savedAt: number;
}

function isNightHour() {
  const h = new Date().getHours();
  return h < 6 || h >= 19;
}

function wmoWeatherIcon(code: number): string {
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

/** US AQI bands (≈国标分段): 0–50 优, 51–100 良, 101–150 中, 151–200 较差, >200 差 */
function aqiLevel(aqi: number | null): string | null {
  if (aqi === null || Number.isNaN(aqi)) return null;
  if (aqi <= 50) return $t('page.home.aqiGood');
  if (aqi <= 100) return $t('page.home.aqiFair');
  if (aqi <= 150) return $t('page.home.aqiModerate');
  if (aqi <= 200) return $t('page.home.aqiPoor');
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

function applySnapshot(
  weather: HomeWeatherState,
  lastWeatherCode: Ref<number | null>,
  lastAqi: Ref<number | null>,
  snapshot: WeatherSnapshot,
) {
  lastWeatherCode.value = snapshot.weatherCode;
  lastAqi.value = snapshot.aqi;
  weather.temp = snapshot.temp;
  weather.humidity = snapshot.humidity;
  weather.windSpeed = snapshot.windSpeed;
  weather.icon = wmoWeatherIcon(snapshot.weatherCode);
  weather.aqi = snapshot.aqi;
  weather.label = wmoLabel(snapshot.weatherCode);
  weather.aqiLevel = aqiLevel(snapshot.aqi);
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

function readWeatherCache(): WeatherCachePayload | null {
  try {
    const raw = localStorage.getItem(WEATHER_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WeatherCachePayload;
    if (
      typeof parsed.savedAt !== 'number' ||
      typeof parsed.weatherCode !== 'number' ||
      Date.now() - parsed.savedAt > WEATHER_CACHE_TTL_MS
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeWeatherCache(snapshot: WeatherSnapshot) {
  try {
    localStorage.setItem(
      WEATHER_CACHE_KEY,
      JSON.stringify({ ...snapshot, savedAt: Date.now() } satisfies WeatherCachePayload),
    );
  } catch {
    /* 隐私模式等场景可能无法写入 */
  }
}

async function fetchOpenMeteoSnapshot(): Promise<WeatherSnapshot> {
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
  aqUrl.searchParams.set('current', 'us_aqi');

  const [forecastRes, aqRes] = await Promise.all([
    fetch(forecastUrl.toString()),
    fetch(aqUrl.toString()).catch(() => null),
  ]);

  if (!forecastRes.ok) throw new Error('Open-Meteo forecast failed');

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

  let aqi: number | null = null;
  if (aqRes?.ok) {
    const aqJson = (await aqRes.json()) as {
      current?: { us_aqi?: number };
    };
    if (aqJson.current?.us_aqi !== undefined) {
      aqi = Math.round(aqJson.current.us_aqi);
    }
  }

  return {
    aqi,
    humidity:
      current.relative_humidity_2m !== undefined
        ? Math.round(current.relative_humidity_2m)
        : null,
    temp:
      current.temperature_2m !== undefined
        ? Math.round(current.temperature_2m)
        : null,
    weatherCode: current.weather_code ?? 3,
    windSpeed:
      current.wind_speed_10m !== undefined
        ? Math.round(current.wind_speed_10m)
        : null,
  };
}

async function fetchWeatherApiSiteSnapshot(): Promise<WeatherSnapshot> {
  const weatherUrl = `https://weather-api.site/weather?lat=${BEIJING_LAT}&lon=${BEIJING_LON}`;
  const aqUrl = `https://weather-api.site/air-quality?lat=${BEIJING_LAT}&lon=${BEIJING_LON}`;

  const [weatherRes, aqRes] = await Promise.all([
    fetch(weatherUrl),
    fetch(aqUrl).catch(() => null),
  ]);

  if (!weatherRes.ok) throw new Error('weather-api.site weather failed');

  const weatherJson = (await weatherRes.json()) as {
    current?: {
      condition_code?: number;
      humidity?: number;
      temperature?: number;
      wind_speed?: number;
    };
  };

  const current = weatherJson.current;
  if (!current) throw new Error('weather-api.site empty');

  let aqi: number | null = null;
  if (aqRes?.ok) {
    const aqJson = (await aqRes.json()) as {
      current?: { us_aqi?: number };
    };
    if (aqJson.current?.us_aqi !== undefined) {
      aqi = Math.round(aqJson.current.us_aqi);
    }
  }

  return {
    aqi,
    humidity:
      current.humidity !== undefined ? Math.round(current.humidity) : null,
    temp:
      current.temperature !== undefined
        ? Math.round(current.temperature)
        : null,
    weatherCode: current.condition_code ?? 3,
    windSpeed:
      current.wind_speed !== undefined
        ? Math.round(current.wind_speed)
        : null,
  };
}

async function raceWeatherProviders(): Promise<WeatherSnapshot> {
  const providers = [fetchOpenMeteoSnapshot(), fetchWeatherApiSiteSnapshot()];

  return new Promise((resolve, reject) => {
    let pending = providers.length;
    let settled = false;
    const errors: unknown[] = [];

    for (const provider of providers) {
      void provider
        .then((snapshot) => {
          if (settled) return;
          settled = true;
          resolve(snapshot);
        })
        .catch((error) => {
          errors.push(error);
          pending -= 1;
          if (pending === 0 && !settled) {
            reject(errors[0] ?? new Error('all weather providers failed'));
          }
        });
    }
  });
}

export function useHomeWeather() {
  const lastWeatherCode = ref<number | null>(null);
  const lastAqi = ref<number | null>(null);

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
    weather.aqiLevel = aqiLevel(lastAqi.value);
  }

  async function loadWeather() {
    const cached = readWeatherCache();
    const hasCache = cached !== null;

    if (hasCache) {
      applySnapshot(weather, lastWeatherCode, lastAqi, cached);
      weather.loading = false;
      applyLocalizedLabels();
    } else {
      weather.loading = true;
      weather.label = $t('page.home.weatherLoading');
    }

    try {
      const snapshot = await raceWeatherProviders();
      applySnapshot(weather, lastWeatherCode, lastAqi, snapshot);
      writeWeatherCache(snapshot);
    } catch {
      if (!hasCache) {
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
