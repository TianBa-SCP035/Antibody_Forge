/**
 * 浏览器本地存储键名。键值一经发布不要改动，否则用户已保存的偏好会丢失；
 * 需要废弃旧数据时在键名后追加版本号。
 */

// localStorage
export const HOME_QUICK_NAV_STORAGE_KEY = 'antibody-vita-home-quick-nav';
export const HOME_WARM_NOTE_STORAGE_KEY = 'antibody-vita-home-warm-note';
/** 登录后默认打开的站内路径（空则跟随服务端 homePath / 系统默认） */
export const HOME_START_PAGE_STORAGE_KEY = 'antibody-vita-user-start-page';
export const WEATHER_CACHE_KEY = 'home-weather-beijing-v4';
export const RECENT_LOGIN_ACCOUNTS_KEY = `ANTIBODY_RECENT_LOGIN_ACCOUNTS_${location.hostname}`;

/** 工作台列顺序、列宽等视图偏好（WorkbenchDataTable 的 storage-key） */
export const WORKBENCH_VIEW_PREFS_KEYS = {
  discovery: 'discoveryWorkbenchViewPrefs.v4',
  library: 'libraryConstructionWorkbench.v4',
  serum: 'serumWorkbenchViewPrefs',
  synthesis: 'discoverySynthesisViewPrefs.v8',
} as const;

// sessionStorage
export const LIST_FILTER_STORAGE_PREFIX = 'listFilters:';
export const DISCOVERY_WORKBENCH_CREATED_KEY = 'discovery.workbench.created';
export const LIBRARY_CREATED_KEY = 'molecular.library.created';
export const TITER_INSTRUMENT_WIZARD_DRAFT_KEY = 'titer-instrument-wizard-draft';
