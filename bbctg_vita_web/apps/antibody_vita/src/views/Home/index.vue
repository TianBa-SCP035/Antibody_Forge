<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { Icon } from '@iconify/vue';
import { ElMessage } from 'element-plus';

import { $t } from '#/locales';

import HomeCalendarPanel from './components/HomeCalendarPanel.vue';
import HomeFeedPanel from './components/HomeFeedPanel.vue';
import HomeHero from './components/HomeHero.vue';
import HomeQuickNav from './components/HomeQuickNav.vue';
import {
  HOME_FEATURED_READ_URL,
  HOME_WARM_NOTE_STORAGE_KEY,
  homePlatformTips,
  useHomeLocalizedMocks,
} from './home-data';

defineOptions({ name: 'Home' });

const { announcements, featuredPick, messages } = useHomeLocalizedMocks();

const note = ref('');
const warmNoteWriting = ref(false);

const warmNoteDisplayText = computed(() => {
  const saved = note.value.trim();
  return saved || $t('page.home.warmNoteQuote');
});

const warmNoteShowSource = computed(() => !note.value.trim());

function openWarmNoteEditor() {
  warmNoteWriting.value = true;
}

function closeWarmNoteEditor() {
  warmNoteWriting.value = false;
}

onMounted(() => {
  try {
    note.value = localStorage.getItem(HOME_WARM_NOTE_STORAGE_KEY) ?? '';
  } catch {
    note.value = '';
  }
});

watch(note, (value) => {
  try {
    localStorage.setItem(HOME_WARM_NOTE_STORAGE_KEY, value);
  } catch {
    /* ignore */
  }
});

function onViewAllAnnouncements() {
  ElMessage.info($t('page.home.announcementsComingSoon'));
}

function onViewAllMessages() {
  ElMessage.info($t('page.home.messagesComingSoon'));
}
</script>

<template>
  <div class="home-page flex w-full flex-col gap-4 p-4 md:gap-5 md:p-5">
    <HomeHero />

    <div class="grid gap-4 md:gap-5 xl:grid-cols-3 xl:items-stretch">
      <div class="flex min-h-0 flex-col gap-4 md:gap-5 xl:h-full">
        <HomeFeedPanel
          class="min-h-0 flex-1"
          variant="announcements"
          :announcements="announcements"
          @view-all="onViewAllAnnouncements"
        />
        <HomeFeedPanel
          class="min-h-0 flex-1"
          variant="messages"
          :messages="messages"
          @view-all="onViewAllMessages"
        />
      </div>

      <div class="flex flex-col gap-4 md:gap-5 xl:h-full">
        <HomeQuickNav />

        <article
          class="overflow-hidden rounded-2xl bg-gradient-to-br from-amber-900/90 via-amber-800/85 to-orange-900/80 p-4 text-amber-50 shadow-sm md:p-5"
        >
          <span
            class="inline-block rounded-md bg-white/15 px-2 py-0.5 text-[10px] font-medium tracking-wide"
          >
            {{ $t('page.home.featuredTag') }}
          </span>
          <h3 class="mt-2 text-lg font-semibold leading-snug">
            {{ featuredPick.title }}
          </h3>
          <p class="mt-1 text-xs text-amber-100/75">{{ featuredPick.author }}</p>
          <blockquote
            class="mt-3 border-l-2 border-amber-200/40 pl-3 text-sm leading-relaxed text-amber-50/90"
          >
            {{ featuredPick.quote }}
          </blockquote>
          <div class="mt-4 flex items-center justify-between gap-2">
            <span class="inline-flex items-center gap-1 text-xs text-amber-100/80">
              <Icon icon="lucide:heart" class="size-3.5" />
              {{ $t('page.home.featuredLikes', { count: featuredPick.likes }) }}
            </span>
            <a
              :href="HOME_FEATURED_READ_URL"
              target="_blank"
              rel="noopener noreferrer"
              class="text-xs font-medium text-amber-50 underline-offset-2 hover:underline"
            >
              {{ $t('page.home.featuredCta') }}
            </a>
          </div>
        </article>

        <div class="home-surface home-warm-note overflow-hidden">
          <div
            class="flex items-center justify-between gap-3 border-b border-border/60 px-4 py-3"
          >
            <div class="flex min-w-0 items-center gap-2.5">
              <span
                class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-500 dark:bg-rose-950/50 dark:text-rose-400"
              >
                <Icon icon="lucide:heart" class="size-4" />
              </span>
              <h2 class="text-base font-semibold">{{ $t('page.home.warmNote') }}</h2>
            </div>
            <p class="shrink-0 text-xs text-foreground/45">
              {{ $t('page.home.warmNoteSubtitle') }}
            </p>
          </div>

          <div class="flex min-h-[8.25rem] flex-col px-4 pb-4">
            <div v-if="warmNoteWriting" class="flex min-h-0 flex-1 flex-col">
              <textarea
                v-model="note"
                class="min-h-[4.5rem] flex-1 resize-none rounded-xl border border-border/60 bg-muted/20 px-3 py-2.5 text-sm leading-relaxed text-foreground/80 outline-none transition-colors placeholder:text-foreground/35 focus:border-primary/40 focus:bg-background"
                :placeholder="$t('page.home.warmNotePlaceholder')"
              />
              <div class="mt-2 flex items-center justify-between gap-2">
                <p class="text-[11px] text-foreground/40">
                  {{ $t('page.home.warmNoteHint') }}
                </p>
                <button
                  type="button"
                  class="shrink-0 text-xs font-medium text-rose-500 hover:text-rose-600"
                  @click="closeWarmNoteEditor"
                >
                  {{ $t('page.home.warmNoteDone') }}
                </button>
              </div>
            </div>

            <div v-else class="flex min-h-0 flex-1 flex-col">
              <div class="flex min-h-0 flex-1 items-center gap-3 py-2">
                <span
                  class="flex size-11 shrink-0 items-center justify-center rounded-full bg-violet-100 text-violet-600 dark:bg-violet-950/45 dark:text-violet-400"
                  aria-hidden="true"
                >
                  <Icon icon="lucide:coffee" class="size-5 shrink-0" />
                </span>
                <p
                  class="min-w-0 flex-1 text-sm italic leading-relaxed text-foreground/70"
                >
                  {{ warmNoteDisplayText }}
                </p>
              </div>
              <div
                class="flex shrink-0 items-center justify-between gap-2 border-t border-border/50 pt-3"
              >
                <span
                  v-if="warmNoteShowSource"
                  class="text-xs text-foreground/45"
                >
                  {{ $t('page.home.warmNoteSource') }}
                </span>
                <span v-else class="flex-1" />
                <button
                  type="button"
                  class="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-rose-500 transition-colors hover:text-rose-600"
                  @click="openWarmNoteEditor"
                >
                  {{ $t('page.home.warmNoteWriteCta') }}
                  <Icon icon="lucide:pencil" class="size-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-4 md:gap-5">
        <HomeCalendarPanel />

        <div class="home-surface px-4 py-3">
          <p class="mb-2 text-xs font-medium text-foreground/50">
            {{ $t('page.home.tipsTitle') }}
          </p>
          <ul class="space-y-2">
            <li
              v-for="(tipKey, index) in homePlatformTips"
              :key="index"
              class="flex gap-2 text-xs leading-relaxed text-foreground/60"
            >
              <Icon
                icon="lucide:sparkles"
                class="mt-0.5 size-3 shrink-0 text-primary/50"
              />
              <span>{{ $t(tipKey) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page :deep(.home-surface) {
  border: 1px solid hsl(var(--border) / 0.65);
  border-radius: 1rem;
  background-color: hsl(var(--card));
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%);
}

.home-page :deep(.home-feed-scroll) {
  scrollbar-color: hsl(var(--border)) transparent;
  scrollbar-width: thin;
}

.home-page :deep(.home-feed-scroll::-webkit-scrollbar) {
  width: 5px;
}

.home-page :deep(.home-feed-scroll::-webkit-scrollbar-thumb) {
  border-radius: 4px;
  background-color: hsl(var(--border));
}

/* 暖心便签：与改版前 textarea 区块接近的固定高度 */
.home-page :deep(.home-warm-note) {
  min-height: 11.5rem;
}
</style>
