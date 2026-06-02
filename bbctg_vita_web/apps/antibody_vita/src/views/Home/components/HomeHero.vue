<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';
import { $t } from '#/locales';

import { useHomeWeather } from '../composables/useHomeWeather';
import { getHomeGreeting } from '../home-data';

defineOptions({ name: 'HomeHero' });

const userStore = useUserStore();
const { weather } = useHomeWeather();
const displayName = computed(
  () =>
    userStore.userInfo?.realName ||
    userStore.userInfo?.username ||
    $t('page.home.defaultUserName'),
);

const greeting = computed(() => {
  void preferences.app.locale;
  return getHomeGreeting();
});

const weatherSubline = computed(() => {
  const parts: string[] = [];
  if (weather.humidity !== null) {
    parts.push($t('page.home.weatherHumidity', { value: weather.humidity }));
  }
  if (weather.windSpeed !== null) {
    parts.push($t('page.home.weatherWind', { value: weather.windSpeed }));
  }
  if (weather.aqiLevel) {
    parts.push(
      $t('page.home.weatherAqi', {
        level: weather.aqiLevel,
        value: weather.aqi ?? '—',
      }),
    );
  }
  return parts;
});

/** 背景图渲染 Meteocons，动画不依赖整页 document 就绪（内联 Icon 会冻住数秒） */
const weatherIconStyle = ref<{ backgroundImage?: string }>({});

async function syncWeatherIconBackground(icon: string) {
  const sep = icon.indexOf(':');
  if (sep < 1) {
    weatherIconStyle.value = {};
    return;
  }
  try {
    const res = await fetch(
      `https://api.iconify.design/${icon.slice(0, sep)}/${icon.slice(sep + 1)}.svg`,
    );
    if (!res.ok) throw new Error('icon fetch failed');
    const svg = (await res.text()).replace(
      '</svg>',
      `<!--${Date.now()}--></svg>`,
    );
    weatherIconStyle.value = {
      backgroundImage: `url("data:image/svg+xml,${encodeURIComponent(svg)}")`,
    };
  } catch {
    weatherIconStyle.value = {};
  }
}

watch(
  () => (weather.loading ? null : weather.icon),
  (icon) => {
    if (icon) void syncWeatherIconBackground(icon);
  },
  { immediate: true },
);
</script>

<template>
  <section
    class="home-hero flex flex-col gap-3 rounded-2xl border px-4 py-4 shadow-sm md:flex-row md:items-center md:justify-between md:px-5 md:py-4"
    role="banner"
  >
    <div class="min-w-0">
      <h1 class="text-lg font-semibold tracking-tight md:text-xl">
        {{ greeting }}，{{ displayName }}
        <span class="home-hero-wave ml-1" aria-hidden="true">👋</span>
      </h1>
      <p class="mt-1 text-sm text-foreground/55">
        {{ $t('page.home.heroStatus') }}
      </p>
      <p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-foreground/50">
        <span>{{ $t('page.home.metricTodo') }} 0</span>
        <span>{{ $t('page.home.metricMessages') }} 0</span>
      </p>
    </div>

    <div
      class="flex w-full shrink-0 items-center gap-3 rounded-2xl border border-border/70 bg-background px-3.5 py-2.5 shadow-sm sm:w-auto sm:min-w-[15rem]"
      role="region"
      :aria-label="$t('page.home.weatherAria')"
    >
      <template v-if="weather.loading">
        <div class="size-11 shrink-0 animate-pulse rounded-xl bg-muted" />
        <div class="flex min-w-0 flex-1 flex-col justify-center gap-1.5">
          <div class="h-4 w-full animate-pulse rounded bg-muted" />
          <div class="h-3 w-4/5 animate-pulse rounded bg-muted" />
        </div>
      </template>
      <template v-else>
        <span
          class="inline-block size-11 shrink-0 bg-contain bg-center bg-no-repeat"
          :style="weatherIconStyle"
          aria-hidden="true"
        />
        <div class="min-w-0 flex-1">
          <div class="flex min-w-0 items-center gap-1.5 leading-none">
            <span
              v-if="weather.temp !== null"
              class="shrink-0 text-base font-semibold tabular-nums text-foreground/90"
            >
              {{ weather.temp }}°C
            </span>
            <template v-if="weather.temp !== null">
              <span class="shrink-0 text-foreground/30" aria-hidden="true">·</span>
            </template>
            <span class="shrink-0 text-sm font-medium text-foreground/85">
              {{ weather.label }}
            </span>
            <span class="ml-auto shrink-0 text-sm font-medium text-foreground/80">
              {{ $t('page.home.weatherCity') }}
            </span>
          </div>
          <p
            v-if="weatherSubline.length"
            class="mt-1.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] leading-relaxed text-foreground/50"
          >
            <span v-for="(part, idx) in weatherSubline" :key="idx">{{ part }}</span>
          </p>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
/* 原型：左淡蓝 → 中薄荷绿 → 右白（三段，不是单色绿渐变） */
.home-hero {
  border-color: rgb(191 219 254 / 45%);
  background: linear-gradient(
    90deg,
    #e6f0ff 0%,
    #f2faf7 46%,
    #ffffff 100%
  );
}

:global(html.dark) .home-hero {
  border-color: hsl(var(--border) / 0.55);
  background: linear-gradient(
    90deg,
    hsl(210 28% 18% / 0.45) 0%,
    hsl(155 12% 16% / 0.22) 46%,
    hsl(var(--card)) 100%
  );
}

.home-hero-wave {
  display: inline-block;
  animation: home-hero-wave-float 2.2s ease-in-out infinite;
}

@keyframes home-hero-wave-float {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-5px);
  }
}
</style>
