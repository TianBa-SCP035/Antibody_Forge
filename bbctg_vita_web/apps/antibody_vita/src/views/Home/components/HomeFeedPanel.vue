<script setup lang="ts">
import { computed } from 'vue';

import { Icon } from '@iconify/vue';

import { $t } from '#/locales';

import type { HomeAnnouncement, HomeMessage } from '../home-data';

defineOptions({ name: 'HomeFeedPanel' });

const props = defineProps<{
  announcements?: HomeAnnouncement[];
  messages?: HomeMessage[];
  variant: 'announcements' | 'messages';
}>();

const emit = defineEmits<{
  viewAll: [];
}>();

const title = computed(() =>
  props.variant === 'announcements'
    ? $t('page.home.announcements')
    : $t('page.home.messages'),
);

const showFooter = computed(() =>
  props.variant === 'announcements'
    ? (props.announcements?.length ?? 0) > 0
    : true,
);
</script>

<template>
  <div class="home-surface flex min-h-0 flex-col overflow-hidden">
    <div class="shrink-0 border-b border-border/60 px-4 py-3">
      <h2 class="text-base font-semibold">{{ title }}</h2>
    </div>

    <div
      class="home-feed-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain"
      :class="
        variant === 'messages' && !(messages?.length ?? 0)
          ? 'flex flex-col items-center justify-center'
          : ''
      "
    >
      <ul
        v-if="variant === 'announcements'"
        class="divide-y divide-border/60 px-2 py-1"
      >
        <li v-for="item in announcements" :key="item.id" class="px-2 py-3">
          <article
            class="rounded-xl px-2 py-2 transition-colors hover:bg-muted/30"
            :class="item.pinned ? 'bg-rose-50/80 dark:bg-rose-950/20' : ''"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="flex min-w-0 items-center gap-2">
                <span class="truncate text-sm font-medium">{{ item.title }}</span>
                <span
                  v-if="item.pinned"
                  class="shrink-0 rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-medium text-rose-600 dark:text-rose-400"
                >
                  {{ $t('page.home.pinned') }}
                </span>
              </div>
              <time class="shrink-0 text-xs text-foreground/45">
                {{ item.publishedAt }}
              </time>
            </div>
            <p class="mt-1.5 line-clamp-3 text-sm leading-relaxed text-foreground/65">
              {{ item.content }}
            </p>
          </article>
        </li>
      </ul>

      <ul
        v-else-if="(messages?.length ?? 0) > 0"
        class="divide-y divide-border/60 px-2 py-1"
      >
        <li
          v-for="item in messages"
          :key="item.id"
          class="flex gap-3 px-2 py-3 transition-colors hover:bg-muted/30"
        >
          <span
            class="flex size-10 shrink-0 items-center justify-center rounded-xl"
            :class="
              item.unread
                ? 'bg-primary/12 text-primary'
                : 'bg-muted/50 text-foreground/50'
            "
          >
            <Icon icon="lucide:mail" class="size-4" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <p class="line-clamp-1 text-sm font-medium">
                <span
                  v-if="item.unread"
                  class="mr-1.5 inline-block size-1.5 rounded-full bg-primary align-middle"
                />
                {{ item.title }}
              </p>
              <time class="shrink-0 text-xs text-foreground/45">{{ item.date }}</time>
            </div>
            <p
              v-if="item.category"
              class="mt-0.5 text-[10px] font-medium text-foreground/45"
            >
              {{ item.category }}
            </p>
            <p class="mt-1 line-clamp-2 text-xs leading-relaxed text-foreground/60">
              {{ item.summary }}
            </p>
          </div>
        </li>
      </ul>

      <template v-else>
        <Icon icon="lucide:inbox" class="mb-2 size-8 text-foreground/25" />
        <p class="text-sm text-foreground/55">{{ $t('page.home.messagesEmpty') }}</p>
        <p class="mt-1 max-w-[12rem] text-xs text-foreground/40">
          {{ $t('page.home.messagesEmptyHint') }}
        </p>
      </template>
    </div>

    <button
      v-if="showFooter"
      type="button"
      class="shrink-0 border-t border-border/60 px-4 py-2.5 text-left text-xs text-primary/80 transition-colors hover:bg-muted/30 hover:text-primary"
      @click="emit('viewAll')"
    >
      {{ $t('page.home.feedViewAllHint') }}
    </button>
  </div>
</template>
