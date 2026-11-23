import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'Home',
    path: '/home',
    component: () => import('#/views/Home/index.vue'),
    meta: {
      icon: 'lucide:home',
      order: 0,
      title: $t('page.home.title'),
    },
  },
];

export default routes;
