/**
 * 首页数据与常量（纯前端占位，接 API 后替换 getter 即可）。
 * 界面文案：locales/page.json 的 page.home.*
 */

import { computed } from 'vue';

import { preferences } from '@vben/preferences';

import { $t } from '#/locales';

const HOME_WEEK_DAYS_ZH = ['一', '二', '三', '四', '五', '六', '日'] as const;
const HOME_WEEK_DAYS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

export function getHomeWeekDayLabels(locale: string): string[] {
  return locale === 'en-US' ? [...HOME_WEEK_DAYS_EN] : [...HOME_WEEK_DAYS_ZH];
}

export interface HomeAnnouncement {
  content: string;
  id: string;
  pinned?: boolean;
  publishedAt: string;
  title: string;
}

export function getHomeAnnouncements(): HomeAnnouncement[] {
  return [
    {
      id: '1',
      title: $t('page.home.mockAnnAdminTitle'),
      content: $t('page.home.mockAnnAdminContent'),
      publishedAt: $t('page.home.mockAnnAdminDate'),
      pinned: true,
    },
    {
      id: '2',
      title: $t('page.home.mockAnnWelcomeTitle'),
      content: $t('page.home.mockAnnWelcomeContent'),
      publishedAt: new Date().toISOString().slice(0, 10),
    },
  ];
}

export interface HomeMessage {
  category?: string;
  date: string;
  id: string;
  summary: string;
  title: string;
  unread?: boolean;
}

export function getHomeMessages(): HomeMessage[] {
  return [
    {
      id: 'msg-1',
      title: $t('page.home.mockMsgWelcomeTitle'),
      summary: $t('page.home.mockMsgWelcomeSummary'),
      date: $t('page.home.mockMsgWelcomeDate'),
      category: $t('page.home.mockMsgWelcomeCategory'),
      unread: false,
    },
  ];
}

export const HOME_QUICK_NAV_SLOTS = 6;

export const HOME_QUICK_NAV_STORAGE_KEY = 'antibody-vita-home-quick-nav';
export const HOME_WARM_NOTE_STORAGE_KEY = 'antibody-vita-home-warm-note';
/** 登录后默认打开的站内路径（空则跟随服务端 homePath / 系统默认） */
export const HOME_START_PAGE_STORAGE_KEY = 'antibody-vita-user-start-page';

export interface QuickNavSlot {
  comingSoon?: boolean;
  external?: boolean;
  icon?: string;
  iconClass?: string;
  presetId?: string;
  subtitle?: string;
  title: string;
  url?: string;
}

export interface QuickNavPresetDef {
  comingSoon?: boolean;
  external?: boolean;
  icon: string;
  iconClass: string;
  id: string;
  subtitleKey: string;
  titleKey: string;
  url: string;
}

export interface QuickNavPresetView extends QuickNavPresetDef {
  subtitle: string;
  title: string;
}

export const homeQuickNavPresetDefs: QuickNavPresetDef[] = [
  {
    id: 'serum-workbench',
    titleKey: 'page.home.presetSerumWorkbenchTitle',
    subtitleKey: 'page.home.presetSerumWorkbenchSubtitle',
    icon: 'lucide:layout-dashboard',
    iconClass: 'bg-blue-500/15 text-blue-600',
    url: '/serum/workbench',
  },
  {
    id: 'serum-list',
    titleKey: 'page.home.presetSerumTitle',
    subtitleKey: 'page.home.presetSerumSubtitle',
    icon: 'lucide:flask-conical',
    iconClass: 'bg-sky-500/15 text-sky-600',
    url: '/serum/list',
  },
  {
    id: 'titer-order-list',
    titleKey: 'page.home.presetTiterOrderTitle',
    subtitleKey: 'page.home.presetTiterOrderSubtitle',
    icon: 'lucide:clipboard-list',
    iconClass: 'bg-indigo-500/15 text-indigo-600',
    url: '/serum/titer-orders',
  },
  {
    id: 'flow-work-order-list',
    titleKey: 'page.home.presetFlowWorkOrderTitle',
    subtitleKey: 'page.home.presetFlowWorkOrderSubtitle',
    icon: 'lucide:workflow',
    iconClass: 'bg-orange-500/15 text-orange-600',
    url: '/mega-automation/flow-work-orders',
  },
  {
    id: 'target-library',
    titleKey: 'page.home.presetTargetLibraryTitle',
    subtitleKey: 'page.home.presetTargetLibrarySubtitle',
    icon: 'lucide:database',
    iconClass: 'bg-cyan-500/15 text-cyan-600',
    url: '/discovery/targets',
  },
  {
    id: 'profile',
    titleKey: 'page.home.presetProfileTitle',
    subtitleKey: 'page.home.presetProfileSubtitle',
    icon: 'lucide:users',
    iconClass: 'bg-emerald-500/15 text-emerald-600',
    url: '/profile',
  },
  {
    id: 'system',
    titleKey: 'page.home.presetSystemTitle',
    subtitleKey: 'page.home.presetSystemSubtitle',
    icon: 'lucide:shield',
    iconClass: 'bg-violet-500/15 text-violet-600',
    url: '/system/user-permission',
  },
  {
    id: 'analytics',
    titleKey: 'page.home.presetAnalyticsTitle',
    subtitleKey: 'page.home.presetAnalyticsSubtitle',
    icon: 'lucide:line-chart',
    iconClass: 'bg-amber-500/15 text-amber-600',
    url: '',
    comingSoon: true,
  },
  {
    id: 'literature',
    titleKey: 'page.home.presetLiteratureTitle',
    subtitleKey: 'page.home.presetLiteratureSubtitle',
    icon: 'lucide:book-open',
    iconClass: 'bg-teal-500/15 text-teal-600',
    url: '',
    comingSoon: true,
  },
  {
    id: 'announcements',
    titleKey: 'page.home.presetAnnouncementsTitle',
    subtitleKey: 'page.home.presetAnnouncementsSubtitle',
    icon: 'lucide:bell',
    iconClass: 'bg-rose-500/15 text-rose-600',
    url: '/home',
  },
];

export const defaultQuickNavPresetIds: Array<string | null> = [
  'serum-list',
  'flow-work-order-list',
  'system',
  'titer-order-list',
  'profile',
  'target-library',
];

export function getQuickNavPresetDef(id: string) {
  return homeQuickNavPresetDefs.find((p) => p.id === id);
}

export function localizeQuickNavPreset(def: QuickNavPresetDef): QuickNavPresetView {
  return {
    ...def,
    title: $t(def.titleKey),
    subtitle: $t(def.subtitleKey),
  };
}

export function getLocalizedQuickNavPresets(): QuickNavPresetView[] {
  return homeQuickNavPresetDefs.map(localizeQuickNavPreset);
}

export function presetToSlot(def: QuickNavPresetDef): QuickNavSlot {
  const localized = localizeQuickNavPreset(def);
  return {
    presetId: def.id,
    title: localized.title,
    subtitle: localized.subtitle,
    icon: def.icon,
    iconClass: def.iconClass,
    url: def.url,
    external: Boolean(def.external),
    comingSoon: def.comingSoon,
  };
}

export const EMPTY_QUICK_NAV_SLOT: QuickNavSlot = {
  title: '',
  subtitle: '',
  icon: 'lucide:plus',
  iconClass: 'bg-muted/40 text-foreground/25',
  url: '',
  external: false,
};

export function slotsFromPresetIds(ids: Array<string | null>): QuickNavSlot[] {
  return Array.from({ length: HOME_QUICK_NAV_SLOTS }, (_, i) => {
    const id = ids[i];
    if (!id) return { ...EMPTY_QUICK_NAV_SLOT };
    const preset = getQuickNavPresetDef(id);
    return preset ? presetToSlot(preset) : { ...EMPTY_QUICK_NAV_SLOT };
  });
}

/** 好书推荐「阅读摘录」固定外链（B 站） */
export const HOME_FEATURED_READ_URL =
  'https://www.bilibili.com/video/BV1GJ411x7h7/?spm_id_from=333.337.search-card.all.click';

export function getHomeFeaturedPick() {
  return {
    title: $t('page.home.featuredTitle'),
    author: $t('page.home.featuredAuthor'),
    quote: $t('page.home.featuredQuote'),
    likes: 128,
  };
}

export interface HomeScheduleItem {
  id: string;
  subtitle?: string;
  time: string;
  title: string;
}

export const homeScheduleByDate: Record<string, HomeScheduleItem[]> = {};

export const homePlatformTips = [
  'page.home.tip1',
  'page.home.tip2',
  'page.home.tip3',
] as const;

export const HOME_SYSTEM_ACCESS_CODES = [
  'system.page.user',
  'system.page.role',
  'system.page.permission',
  'system.page.operation_log',
  'system.page.feature',
] as const;

export function normalizeInternalPath(input: string): string {
  const trimmed = input.trim();
  if (!trimmed || /^https?:\/\//i.test(trimmed) || trimmed.startsWith('//')) {
    return '';
  }
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

export function loadUserStartPagePath(): string | null {
  try {
    const raw = localStorage.getItem(HOME_START_PAGE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { path?: string };
    const path = normalizeInternalPath(String(parsed?.path ?? ''));
    return path || null;
  } catch {
    /* ignore */
  }
  return null;
}

export function saveUserStartPagePath(path: string | null) {
  try {
    if (!path) {
      localStorage.removeItem(HOME_START_PAGE_STORAGE_KEY);
      return;
    }
    localStorage.setItem(
      HOME_START_PAGE_STORAGE_KEY,
      JSON.stringify({ path: normalizeInternalPath(path) }),
    );
  } catch {
    /* ignore */
  }
}

export function canAccessStartPath(
  path: string,
  hasAccessByCodes: (codes: string[]) => boolean,
): boolean {
  if (path === '/serum/workbench') {
    return hasAccessByCodes(['serum.page.workbench']);
  }
  if (path === '/serum/list') {
    return hasAccessByCodes(['serum.page.list']);
  }
  if (path === '/serum/titer-orders') {
    return hasAccessByCodes(['serum.page.titer_order']);
  }
  if (path === '/mega-automation/flow-work-orders') {
    return hasAccessByCodes(['mega.page.flow_work_order']);
  }
  if (path === '/discovery/targets') {
    return hasAccessByCodes(['discovery.page.target_library']);
  }
  if (path.startsWith('/system')) {
    return hasAccessByCodes([...HOME_SYSTEM_ACCESS_CODES]);
  }
  return true;
}

export function resolveUserStartPath(
  serverHomePath: string | undefined,
  hasAccessByCodes: (codes: string[]) => boolean,
): string {
  const fallback = serverHomePath || preferences.app.defaultHomePath;
  const custom = loadUserStartPagePath();
  if (!custom) return fallback;
  if (!canAccessStartPath(custom, hasAccessByCodes)) return fallback;
  return custom;
}

/** 快捷导航格子对应的站内路径（外链/占位/即将上线返回 null） */
export function quickNavSlotPath(slot: QuickNavSlot): string | null {
  if (slot.comingSoon) return null;
  const url = (slot.url ?? '').trim();
  if (!url || slot.external || /^https?:\/\//i.test(url) || url.startsWith('//')) {
    return null;
  }
  const path = normalizeInternalPath(url);
  return path || null;
}

export function createAccessChecker(
  accessCodes: string[],
): (codes: string[]) => boolean {
  const set = new Set(accessCodes);
  return (codes: string[]) => codes.some((code) => set.has(code));
}

export function getHomeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return $t('page.home.greetingMorning');
  if (hour < 18) return $t('page.home.greetingAfternoon');
  return $t('page.home.greetingEvening');
}

/** mock 数据随语言切换自动更新 */
export function useHomeLocalizedMocks() {
  const announcements = computed(() => {
    void preferences.app.locale;
    return getHomeAnnouncements();
  });
  const messages = computed(() => {
    void preferences.app.locale;
    return getHomeMessages();
  });
  const featuredPick = computed(() => {
    void preferences.app.locale;
    return getHomeFeaturedPick();
  });
  return { announcements, featuredPick, messages };
}
