import { defineOverridesPreferences } from '@vben/preferences';

/** 只覆盖项目自定义配置；修改后需清空缓存才能稳定生效。 */
export const overridesPreferences = defineOverridesPreferences({
  app: {
    defaultHomePath: '/home',
    defaultAvatar: '/Vita256.ico',
  },
  copyright: {
    companyName: 'Biocytogen',
    companySiteLink: 'https://www.biocytogen.com.cn',
    date: '2026',
    enable: true,
  },
  logo: {
    enable: true,
    fit: 'contain',
    source: '/Vita.png',
    sourceDark: '/Vita.png',
  },
  theme: {
    mode: 'light',
  },
  tabbar: {
    maxCount: 10,
  },
  transition: {
    enable: true,
    name: 'fade-slide',
  },
});
