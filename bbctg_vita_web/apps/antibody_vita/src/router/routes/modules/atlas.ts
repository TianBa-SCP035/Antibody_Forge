import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['atlas.page.target_library'],
      featureCode: 'menu.atlas',
      icon: 'lucide:network',
      order: 5,
      title: '千鼠万抗',
    },
    name: 'Atlas',
    path: '/atlas',
    redirect: '/atlas/targets',
    children: [
      {
        name: 'AtlasTargetLibrary',
        path: '/atlas/targets',
        component: () => import('#/views/Atlas/TargetLibrary/TargetLibrary.vue'),
        meta: {
          authority: ['atlas.page.target_library'],
          featureCode: 'menu.atlas.target_library',
          icon: 'lucide:database',
          keepAlive: true,
          title: '靶点情报',
        },
      },
    ],
  },
];

export default routes;
