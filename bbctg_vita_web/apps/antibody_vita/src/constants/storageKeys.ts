/**
 * 全站共用的浏览器本地存储键名；只属于某个模块的键放在模块自己的文件里。键值一经发布不要改动，否则用户已保存的偏好会丢失；
 * 需要废弃旧数据时在键名后追加版本号。
 */

// localStorage
export const HOME_QUICK_NAV_STORAGE_KEY = 'antibody-vita-home-quick-nav';
export const HOME_WARM_NOTE_STORAGE_KEY = 'antibody-vita-home-warm-note';
/** 登录后默认打开的站内路径（空则跟随服务端 homePath / 系统默认） */
export const HOME_START_PAGE_STORAGE_KEY = 'antibody-vita-user-start-page';
export const WEATHER_CACHE_KEY = 'home-weather-beijing-v4';
export const RECENT_LOGIN_ACCOUNTS_KEY = `ANTIBODY_RECENT_LOGIN_ACCOUNTS_${location.hostname}`;

// sessionStorage
export const LIST_FILTER_STORAGE_PREFIX = 'listFilters:';
