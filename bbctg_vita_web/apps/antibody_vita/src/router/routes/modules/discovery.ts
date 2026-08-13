import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['discovery.page.target_library'],
      featureCode: 'menu.discovery',
      icon: 'lucide:network',
      order: 5,
      title: '千鼠万抗',
    },
    name: 'Discovery',
    path: '/discovery',
    redirect: '/discovery/targets',
    children: [
      {
        name: 'DiscoveryTargetLibrary',
        path: '/discovery/targets',
        component: () => import('#/views/Discovery/TargetLibrary/TargetLibrary.vue'),
        meta: {
          authority: ['discovery.page.target_library'],
          featureCode: 'menu.discovery.target_library',
          icon: 'lucide:database',
          keepAlive: true,
          title: '靶点情报',
        },
      },
    ],
  },
];

export default routes;
