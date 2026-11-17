import { createApp, watchEffect } from 'vue';

import { registerAccessDirective } from '@vben/access';
import { registerLoadingDirective } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { initStores } from '@vben/stores';
import '@vben/styles';
import 'element-plus/theme-chalk/dark/css-vars.css';

import './styles/theme.css';
import './styles/list-page-surface.css';
import './styles/isolated-loading.css';

import { useTitle } from '@vueuse/core';

import { $t, setupI18n } from '#/locales';

import { initSessionExpiryWatcher } from '#/utils/auth-session';
import { isolatedLoadingDirective } from '#/utils/isolatedLoading';
import { initTableContextMenu } from '#/utils/tableContextMenu';

import { initComponentAdapter } from './adapter/component';
import { initSetupVbenForm } from './adapter/form';
import App from './app.vue';
import { router } from './router';

async function bootstrap(namespace: string) {
  await initComponentAdapter();

  await initSetupVbenForm();

  const app = createApp(App);

  app.directive('loading', isolatedLoadingDirective);

  registerLoadingDirective(app, {
    loading: false, // v-loading 使用 Element Plus 实现，避免与 Vben 指令冲突。
    spinning: 'spinning',
  });

  await setupI18n(app);

  await initStores(app, { namespace });

  registerAccessDirective(app);

  const { initTippy } = await import('@vben/common-ui/es/tippy');
  initTippy(app);

  app.use(router);
  initSessionExpiryWatcher();
  initTableContextMenu();

  const { MotionPlugin } = await import('@vben/plugins/motion');
  app.use(MotionPlugin);

  watchEffect(() => {
    if (preferences.app.dynamicTitle) {
      const routeTitle = router.currentRoute.value.meta?.title;
      // 标签页后缀用 VITE_APP_TITLE（如 Antibody Vita）；左上角文案用 preferences.app.name
      const tabSuffix = import.meta.env.VITE_APP_TITLE || preferences.app.name;
      const pageTitle =
        (routeTitle ? `${$t(routeTitle)} - ` : '') + tabSuffix;
      useTitle(pageTitle);
    }
  });

  app.mount('#app');
}

export { bootstrap };
