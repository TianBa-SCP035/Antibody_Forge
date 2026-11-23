import { initPreferences } from '@vben/preferences';
import { unmountGlobalLoading } from '@vben/utils';

import { overridesPreferences } from './preferences';

async function initApplication() {
  // 命名空间隔离不同应用版本和环境的偏好设置与存储数据。
  const env = import.meta.env.PROD ? 'prod' : 'dev';
  const appVersion = import.meta.env.VITE_APP_VERSION;
  const namespace = `${import.meta.env.VITE_APP_NAMESPACE}-${appVersion}-${env}`;

  await initPreferences({
    namespace,
    overrides: overridesPreferences,
  });

  const { bootstrap } = await import('./bootstrap');
  await bootstrap(namespace);

  unmountGlobalLoading();
}

if ((window as Window & { __VITA_UNSUPPORTED_BROWSER__?: boolean }).__VITA_UNSUPPORTED_BROWSER__) {
  unmountGlobalLoading();
} else {
  initApplication();
}
