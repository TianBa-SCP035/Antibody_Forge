<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { preferences } from '@vben/preferences';
import { useRouter } from 'vue-router';

import { useAccess } from '@vben/access';
import { IconifyIcon as Icon } from '@vben/icons';
import { ElButton, ElDialog, ElMessage } from 'element-plus';

import { $t } from '#/locales';

import {
  canAccessStartPath,
  defaultQuickNavPresetIds,
  EMPTY_QUICK_NAV_SLOT,
  getLocalizedQuickNavPresets,
  getQuickNavPresetDef,
  HOME_QUICK_NAV_SLOTS,
  HOME_QUICK_NAV_STORAGE_KEY,
  homeQuickNavPresetDefs,
  loadUserStartPagePath,
  presetToSlot,
  quickNavSlotPath,
  saveUserStartPagePath,
  slotsFromPresetIds,
  type QuickNavPresetDef,
  type QuickNavPresetView,
  type QuickNavSlot,
} from '../home-data';

defineOptions({ name: 'HomeQuickNav' });

const router = useRouter();
const { hasAccessByCodes } = useAccess();

function slotToPresetId(slot: QuickNavSlot): string | null {
  if (slot.presetId) return slot.presetId;
  const url = (slot.url ?? '').trim();
  if (!url) return null;
  const match = homeQuickNavPresetDefs.find((p) => p.url === url);
  return match?.id ?? null;
}

function loadPresetIds(): Array<string | null> {
  try {
    const raw = localStorage.getItem(HOME_QUICK_NAV_STORAGE_KEY);
    if (!raw) return [...defaultQuickNavPresetIds];

    const parsed = JSON.parse(raw) as unknown;

    if (
      Array.isArray(parsed) &&
      parsed.length > 0 &&
      (typeof parsed[0] === 'string' || parsed[0] === null)
    ) {
      return Array.from({ length: HOME_QUICK_NAV_SLOTS }, (_, i) => {
        const id = parsed[i];
        return typeof id === 'string' ? id : null;
      });
    }

    if (Array.isArray(parsed) && parsed[0] && typeof parsed[0] === 'object') {
      return Array.from({ length: HOME_QUICK_NAV_SLOTS }, (_, i) => {
        const legacy = parsed[i] as QuickNavSlot | undefined;
        return legacy ? slotToPresetId(legacy) : null;
      });
    }
  } catch {
    /* ignore */
  }
  return [...defaultQuickNavPresetIds];
}

function isSlotEmpty(slot: QuickNavSlot) {
  return !slot.presetId && !(slot.url ?? '').trim();
}

function persistSlots(next: QuickNavSlot[]) {
  try {
    const ids = next.map((s) => slotToPresetId(s));
    localStorage.setItem(HOME_QUICK_NAV_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* ignore */
  }
}

const slots = ref<QuickNavSlot[]>(slotsFromPresetIds(loadPresetIds()));
const localizedPresets = computed(() => {
  void preferences.app.locale;
  return getLocalizedQuickNavPresets();
});

const customizeVisible = ref(false);
const draft = ref<QuickNavSlot[]>([]);
const dragPresetId = ref<string | null>(null);
const draftStartPagePath = ref<string | null>(null);

watch(customizeVisible, (open) => {
  if (open) {
    draft.value = slots.value.map((s) => ({ ...s }));
    draftStartPagePath.value = loadUserStartPagePath();
  }
});

watch(
  () => preferences.app.locale,
  () => {
    slots.value = slotsFromPresetIds(slots.value.map((s) => slotToPresetId(s)));
  },
);

function openCustomize() {
  customizeVisible.value = true;
}

function closeCustomize() {
  customizeVisible.value = false;
}

function isSlotStartPage(index: number) {
  const path = quickNavSlotPath(draft.value[index]!);
  return !!path && path === draftStartPagePath.value;
}

function toggleSlotStartPage(index: number) {
  const slot = draft.value[index];
  if (!slot || isSlotEmpty(slot)) return;

  const path = quickNavSlotPath(slot);
  if (!path) {
    ElMessage.info($t('page.home.startPageSlotUnavailable'));
    return;
  }

  if (draftStartPagePath.value === path) {
    draftStartPagePath.value = null;
    return;
  }

  if (!canAccessStartPath(path, hasAccessByCodes)) {
    ElMessage.warning($t('page.home.startPageNoPermission'));
    return;
  }

  draftStartPagePath.value = path;
}

function resolveSavedStartPagePath(nextSlots: QuickNavSlot[]): string | null {
  const path = draftStartPagePath.value;
  if (!path) return null;
  const inGrid = nextSlots.some((s) => quickNavSlotPath(s) === path);
  if (!inGrid) return null;
  if (!canAccessStartPath(path, hasAccessByCodes)) return null;
  return path;
}

function saveCustomize() {
  const nextSlots = draft.value.map((s) => {
    if (isSlotEmpty(s)) return { ...EMPTY_QUICK_NAV_SLOT };
    if (s.presetId) {
      const preset = getQuickNavPresetDef(s.presetId);
      if (preset) return presetToSlot(preset);
    }
    return { ...s };
  });

  slots.value = nextSlots;
  persistSlots(slots.value);
  saveUserStartPagePath(resolveSavedStartPagePath(nextSlots));
  closeCustomize();
  ElMessage.success($t('page.home.quickNavSaveSuccess'));
}

function resetDraftToDefault() {
  draft.value = slotsFromPresetIds(defaultQuickNavPresetIds);
  draftStartPagePath.value = null;
}

function assignPreset(index: number, preset: QuickNavPresetDef) {
  const prevPath = quickNavSlotPath(draft.value[index]!);
  const next = [...draft.value];
  next[index] = presetToSlot(preset);
  draft.value = next;
  if (prevPath && draftStartPagePath.value === prevPath) {
    draftStartPagePath.value = null;
  }
}

function clearSlot(index: number) {
  const prevPath = quickNavSlotPath(draft.value[index]!);
  const next = [...draft.value];
  next[index] = { ...EMPTY_QUICK_NAV_SLOT };
  draft.value = next;
  if (prevPath && draftStartPagePath.value === prevPath) {
    draftStartPagePath.value = null;
  }
}

function onPresetDragStart(presetId: string) {
  dragPresetId.value = presetId;
}

function onDragOver(event: DragEvent) {
  event.preventDefault();
}

function onSlotDrop(index: number) {
  const preset = homeQuickNavPresetDefs.find((p) => p.id === dragPresetId.value);
  if (preset) assignPreset(index, preset);
  dragPresetId.value = null;
}

function onPresetClick(preset: QuickNavPresetView) {
  const def = getQuickNavPresetDef(preset.id);
  if (!def) return;
  const emptyIndex = draft.value.findIndex(
    (s) => !s.presetId && !(s.url ?? '').trim(),
  );
  assignPreset(emptyIndex === -1 ? 0 : emptyIndex, def);
}

function navigateInternal(url: string) {
  const path = url.startsWith('/') ? url : `/${url}`;
  if (!canAccessStartPath(path, hasAccessByCodes)) {
    ElMessage.warning($t('page.home.noPermission'));
    return;
  }
  router.push(path);
}

function onActivate(slot: QuickNavSlot) {
  if (isSlotEmpty(slot)) {
    openCustomize();
    return;
  }

  if (slot.comingSoon) {
    ElMessage.info($t('page.home.comingSoon'));
    return;
  }

  const url = (slot.url ?? '').trim();
  if (!url) {
    ElMessage.info($t('page.home.comingSoon'));
    return;
  }

  const isExternal =
    slot.external || /^https?:\/\//i.test(url) || url.startsWith('//');

  if (isExternal) {
    const href = url.startsWith('//') ? `https:${url}` : url;
    window.open(href, '_blank', 'noopener,noreferrer');
    return;
  }

  navigateInternal(url);
}
</script>

<template>
  <div class="home-surface overflow-hidden">
    <div
      class="flex items-center justify-between gap-2 border-b border-border/60 px-4 py-3"
    >
      <div class="flex min-w-0 items-center gap-2">
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
        >
          <Icon icon="lucide:layout-grid" class="size-4" />
        </span>
        <h2 class="truncate text-base font-semibold">
          {{ $t('page.home.quickNav') }}
        </h2>
      </div>
      <button
        type="button"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-foreground/55 transition-colors hover:bg-muted hover:text-foreground"
        @click="openCustomize"
      >
        <Icon icon="lucide:settings" class="size-3.5" />
        {{ $t('page.home.quickNavCustomize') }}
      </button>
    </div>

    <div class="grid grid-cols-3 gap-2.5 p-3">
      <button
        v-for="(slot, index) in slots"
        :key="index"
        type="button"
        class="flex min-h-[6.75rem] flex-col items-center justify-center gap-2 rounded-xl border border-border/55 bg-background px-2 py-3 text-center transition-all hover:border-primary/30 hover:shadow-sm"
        :class="
          isSlotEmpty(slot)
            ? 'border-dashed bg-muted/10 hover:border-border/55 hover:shadow-none'
            : ''
        "
        @click="onActivate(slot)"
      >
        <template v-if="isSlotEmpty(slot)">
          <span
            class="flex size-11 items-center justify-center rounded-xl bg-muted/40 text-foreground/25"
          >
            <Icon icon="lucide:plus" class="size-5" />
          </span>
          <span class="text-xs text-foreground/40">{{ $t('page.home.slotEmpty') }}</span>
        </template>
        <template v-else>
          <span
            class="flex size-11 items-center justify-center rounded-xl"
            :class="slot.iconClass || 'bg-muted text-foreground/60'"
          >
            <Icon v-if="slot.icon" :icon="slot.icon" class="size-5" />
          </span>
          <div class="min-w-0 w-full">
            <p class="truncate text-sm font-semibold leading-tight">
              {{ slot.title }}
            </p>
            <p
              v-if="slot.subtitle"
              class="mt-1 line-clamp-2 text-[11px] leading-snug text-foreground/45"
            >
              {{ slot.subtitle }}
            </p>
          </div>
        </template>
      </button>
    </div>
  </div>

  <ElDialog
    v-model="customizeVisible"
    :title="$t('page.home.quickNavCustomizeTitle')"
    width="560px"
    class="home-quick-nav-dialog"
    destroy-on-close
    align-center
  >
    <section class="qn-section">
      <p class="qn-dialog-hint">{{ $t('page.home.quickNavCustomizeHint') }}</p>
      <div class="qn-slot-grid">
        <div
          v-for="(slot, index) in draft"
          :key="`slot-${index}`"
          class="qn-slot"
          :class="[
            isSlotEmpty(slot) ? 'qn-slot--empty' : 'qn-slot--filled',
            isSlotStartPage(index) ? 'qn-slot--default' : '',
          ]"
          @dragover="onDragOver"
          @drop="onSlotDrop(index)"
        >
          <button
            v-if="!isSlotEmpty(slot)"
            type="button"
            class="qn-slot-remove"
            :title="$t('page.home.quickNavRemoveSlot')"
            @click.stop="clearSlot(index)"
          >
            <Icon icon="lucide:x" class="size-3.5" />
          </button>

          <button
            v-if="!isSlotEmpty(slot)"
            type="button"
            class="qn-slot-body"
            :title="
              isSlotStartPage(index)
                ? $t('page.home.startPageUnsetHint')
                : $t('page.home.startPageSetHint')
            "
            @click.stop="toggleSlotStartPage(index)"
          >
            <span
              v-if="isSlotStartPage(index)"
              class="qn-default-badge"
            >
              <Icon icon="lucide:check" class="size-2.5" />
              {{ $t('page.home.startPageBadge') }}
            </span>
            <span class="qn-chip-icon" :class="slot.iconClass">
              <Icon :icon="slot.icon!" class="size-4" />
            </span>
            <p class="qn-slot-label">{{ slot.title }}</p>
          </button>

          <template v-else>
            <Icon icon="lucide:plus" class="size-4 text-foreground/30" />
            <span class="qn-slot-placeholder">{{ $t('page.home.quickNavDropHere') }}</span>
          </template>
        </div>
      </div>
    </section>

    <section class="qn-section qn-section--last">
      <p class="mb-2 text-xs font-medium text-foreground/45">
        {{ $t('page.home.quickNavPaletteLabel') }}
      </p>
      <div class="qn-palette-grid">
        <button
          v-for="preset in localizedPresets"
          :key="preset.id"
          type="button"
          draggable="true"
          class="qn-palette-item"
          :class="{ 'qn-palette-item--soon': preset.comingSoon }"
          @click="onPresetClick(preset)"
          @dragstart="onPresetDragStart(preset.id)"
        >
          <span class="qn-chip-icon shrink-0" :class="preset.iconClass">
            <Icon :icon="preset.icon" class="size-4" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="qn-palette-title">{{ preset.title }}</span>
            <span
              v-if="preset.comingSoon"
              class="qn-palette-badge"
            >
              {{ $t('page.home.comingSoon') }}
            </span>
          </span>
        </button>
      </div>
    </section>

    <template #footer>
      <div class="flex w-full flex-wrap items-center gap-2">
        <ElButton text type="info" @click="resetDraftToDefault">
          {{ $t('page.home.quickNavReset') }}
        </ElButton>
        <div class="flex-1" />
        <ElButton @click="closeCustomize">{{ $t('page.home.actionCancel') }}</ElButton>
        <ElButton type="primary" @click="saveCustomize">
          {{ $t('page.home.actionSave') }}
        </ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped>
.qn-section {
  margin-bottom: 1.25rem;
}

.qn-section--last {
  margin-bottom: 0;
}

.qn-dialog-hint {
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
  line-height: 1.4;
  color: hsl(var(--foreground) / 0.5);
}

.qn-chip-icon {
  display: flex;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
}

.qn-slot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.qn-slot {
  position: relative;
  display: flex;
  height: 5.75rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 0.375rem;
  border-radius: 0.75rem;
  text-align: center;
  transition:
    border-color 0.15s,
    box-shadow 0.15s,
    background 0.15s;
}

.qn-slot--empty {
  border: 1px dashed hsl(var(--border));
  background: hsl(var(--muted) / 0.2);
}

.qn-slot--filled {
  border: 1px solid hsl(var(--border) / 0.7);
  background: hsl(var(--background));
}

.qn-slot--default {
  border-color: hsl(var(--primary) / 0.55);
  background: hsl(var(--primary) / 0.05);
  box-shadow: 0 0 0 1px hsl(var(--primary) / 0.15);
}

.qn-slot-body {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.25rem;
  border-radius: 0.5rem;
  cursor: pointer;
}

.qn-slot-body:hover {
  background: hsl(var(--muted) / 0.25);
}

.qn-default-badge {
  position: absolute;
  top: 0.375rem;
  left: 0.375rem;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  padding: 0.125rem 0.375rem;
  border-radius: 9999px;
  font-size: 0.5625rem;
  font-weight: 600;
  line-height: 1;
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.12);
}

.qn-slot-remove {
  position: absolute;
  top: 0.3125rem;
  right: 0.3125rem;
  z-index: 2;
  display: flex;
  width: 1.375rem;
  height: 1.375rem;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: 0.375rem;
  background: hsl(var(--background));
  color: hsl(var(--foreground) / 0.7);
  box-shadow: 0 1px 2px rgb(0 0 0 / 6%);
}

.qn-slot-remove:hover {
  border-color: hsl(0 72% 51% / 0.45);
  background: hsl(0 72% 51% / 0.08);
  color: hsl(0 72% 45%);
}

.qn-slot-label {
  display: -webkit-box;
  overflow: hidden;
  width: 100%;
  padding: 0 0.25rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.25;
}

.qn-slot-placeholder {
  font-size: 0.625rem;
  color: hsl(var(--foreground) / 0.38);
}

.qn-palette-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  max-height: 15rem;
  overflow-y: auto;
  padding: 0.125rem 0.25rem 0.125rem 0;
  scrollbar-width: thin;
}

.qn-palette-grid::-webkit-scrollbar {
  width: 4px;
}

.qn-palette-grid::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: hsl(var(--border));
}

.qn-palette-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 3rem;
  padding: 0.5rem 0.625rem;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: 0.75rem;
  background: hsl(var(--background));
  text-align: left;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.qn-palette-item:hover {
  border-color: hsl(var(--primary) / 0.3);
  background: hsl(var(--muted) / 0.3);
}

.qn-palette-item--soon {
  opacity: 0.65;
}

.qn-palette-title {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.25;
}

.qn-palette-badge {
  display: block;
  margin-top: 0.125rem;
  font-size: 0.625rem;
  color: hsl(var(--foreground) / 0.4);
}
</style>
