<script setup lang="ts">
import { computed, ref } from 'vue';

import { preferences } from '@vben/preferences';
import { IconifyIcon as Icon } from '@vben/icons';
import dayjs, { type Dayjs } from 'dayjs';
import 'dayjs/locale/en';
import 'dayjs/locale/zh-cn';
import isoWeek from 'dayjs/plugin/isoWeek';

import { $t } from '#/locales';

import { getHomeWeekDayLabels, homeScheduleByDate } from '../home-data';

dayjs.extend(isoWeek);

defineOptions({ name: 'HomeCalendarPanel' });

type HomeCalendarCell = {
  date: Dayjs;
  inMonth: boolean;
  isSelected: boolean;
  isToday: boolean;
};

const viewMonth = ref(dayjs().startOf('month'));
const selectedDay = ref(dayjs().startOf('day'));

const weekLabels = computed(() =>
  getHomeWeekDayLabels(preferences.app.locale),
);

function dayjsLocale() {
  return preferences.app.locale === 'en-US' ? 'en' : 'zh-cn';
}

const monthTitle = computed(() => {
  const d = viewMonth.value.locale(dayjsLocale());
  return preferences.app.locale === 'en-US'
    ? d.format('MMMM YYYY')
    : d.format('YYYY年 M月');
});

const selectedLabel = computed(() => {
  const d = selectedDay.value.locale(dayjsLocale());
  return preferences.app.locale === 'en-US'
    ? d.format('dddd, MMM D')
    : d.format('M月D日 dddd');
});
const selectedDayKey = computed(() => selectedDay.value.format('YYYY-MM-DD'));
const scheduleItems = computed(
  () => homeScheduleByDate[selectedDayKey.value] ?? [],
);
const scheduleDates = computed(
  () => new Set(Object.keys(homeScheduleByDate)),
);
const hasSchedule = computed(() => scheduleItems.value.length > 0);

const calendarCells = computed(() => {
  const start = viewMonth.value.startOf('month').startOf('isoWeek');
  const end = viewMonth.value.endOf('month').endOf('isoWeek');
  const cells: HomeCalendarCell[] = [];
  let cursor = start;

  while (cursor.isBefore(end) || cursor.isSame(end, 'day')) {
    cells.push({
      date: cursor,
      inMonth: cursor.month() === viewMonth.value.month(),
      isSelected: cursor.isSame(selectedDay.value, 'day'),
      isToday: cursor.isSame(dayjs(), 'day'),
    });
    cursor = cursor.add(1, 'day');
  }
  return cells;
});

function hasEventsOn(date: Dayjs) {
  return scheduleDates.value.has(date.format('YYYY-MM-DD'));
}

function prevMonth() {
  viewMonth.value = viewMonth.value.subtract(1, 'month');
}

function nextMonth() {
  viewMonth.value = viewMonth.value.add(1, 'month');
}

function selectDay(date: Dayjs) {
  selectedDay.value = date.startOf('day');
  if (date.month() !== viewMonth.value.month()) {
    viewMonth.value = date.startOf('month');
  }
}

function goToToday() {
  const today = dayjs().startOf('day');
  selectedDay.value = today;
  viewMonth.value = today.startOf('month');
}
</script>

<template>
  <div class="home-surface flex min-h-0 flex-col overflow-hidden">
    <div class="shrink-0 border-b border-border/60 px-4 py-3">
      <div class="flex items-center justify-between gap-2">
        <div>
          <h2 class="text-base font-semibold">{{ $t('page.home.calendar') }}</h2>
          <p class="text-xs text-foreground/50">
            {{ $t('page.home.calendarSubtitle') }}
          </p>
        </div>
        <div class="flex items-center gap-0.5">
          <button
            type="button"
            class="rounded-md px-2 py-0.5 text-xs text-primary hover:bg-primary/10"
            @click="goToToday"
          >
            {{ $t('page.home.goToday') }}
          </button>
          <button
            type="button"
            class="flex size-7 items-center justify-center rounded-md text-sm hover:bg-muted"
            aria-label="previous month"
            @click="prevMonth"
          >
            ‹
          </button>
          <span class="min-w-[5.5rem] text-center text-xs font-medium tabular-nums">
            {{ monthTitle }}
          </span>
          <button
            type="button"
            class="flex size-7 items-center justify-center rounded-md text-sm hover:bg-muted"
            aria-label="next month"
            @click="nextMonth"
          >
            ›
          </button>
        </div>
      </div>
    </div>

    <div class="shrink-0 px-4 py-3">
      <p class="mb-2 text-xs text-foreground/55">{{ selectedLabel }}</p>

      <div class="grid grid-cols-7 gap-1">
        <div
          v-for="(label, idx) in weekLabels"
          :key="`w-${idx}`"
          class="flex h-7 min-w-0 items-center justify-center text-[11px] font-medium text-foreground/45"
        >
          {{ label }}
        </div>

        <button
          v-for="(cell, idx) in calendarCells"
          :key="idx"
          type="button"
          class="relative flex h-9 min-w-0 items-center justify-center rounded-lg text-[13px] tabular-nums transition-colors"
          :class="{
            'text-foreground/30': !cell.inMonth,
            'bg-primary font-semibold text-primary-foreground shadow-sm':
              cell.isSelected,
            'font-semibold text-primary ring-1 ring-primary/35':
              cell.isToday && !cell.isSelected,
            'hover:bg-muted/55': !cell.isSelected,
          }"
          @click="selectDay(cell.date)"
        >
          <span>{{ cell.date.date() }}</span>
          <span
            v-if="hasEventsOn(cell.date)"
            class="absolute bottom-1 left-1/2 size-1 -translate-x-1/2 rounded-full"
            :class="cell.isSelected ? 'bg-primary-foreground' : 'bg-primary'"
          />
        </button>
      </div>
    </div>

    <div class="flex min-h-[10rem] flex-1 flex-col border-t border-border/40 px-4 py-3">
      <p class="mb-2 text-sm font-medium">{{ $t('page.home.schedule') }}</p>

      <div
        v-if="hasSchedule"
        class="home-feed-scroll min-h-0 flex-1 space-y-0 overflow-y-auto pr-1"
      >
        <div
          v-for="(item, index) in scheduleItems"
          :key="item.id"
          class="relative flex gap-3 pb-4 last:pb-0"
        >
          <div class="flex flex-col items-center">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary"
            >
              {{ index + 1 }}
            </span>
            <span
              v-if="index < scheduleItems.length - 1"
              class="mt-1 w-px flex-1 bg-border"
            />
          </div>
          <div class="min-w-0 flex-1 pt-0.5">
            <p class="text-[11px] tabular-nums text-foreground/50">
              {{ item.time }}
            </p>
            <p class="mt-0.5 text-sm font-medium leading-snug">{{ item.title }}</p>
            <p
              v-if="item.subtitle"
              class="mt-0.5 text-xs text-foreground/55"
            >
              {{ item.subtitle }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-else
        class="flex flex-1 flex-col items-center justify-center rounded-xl bg-muted/20 px-3 py-6 text-center"
      >
        <Icon icon="lucide:calendar-clock" class="mb-2 size-7 text-foreground/25" />
        <p class="text-xs leading-relaxed text-foreground/50">
          {{ $t('page.home.scheduleEmptyShort') }}
        </p>
      </div>
    </div>
  </div>
</template>
