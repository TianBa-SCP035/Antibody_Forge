import type { RouteRecordRaw } from 'vue-router';

const DISCOVERY_WORKBENCH_TAB_GROUP = '/discovery/workbench';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['discovery.page.workbench'],
      featureCode: 'menu.discovery',
      icon: 'lucide:microscope',
      order: 15,
      title: '抗体发现',
    },
    name: 'Discovery',
    path: '/discovery',
    redirect: '/discovery/workbench',
    children: [
      {
        name: 'DiscoveryWorkbench',
        path: '/discovery/workbench',
        component: () => import('#/views/Discovery/workbench/DiscoveryWorkbench.vue'),
        meta: {
          authority: ['discovery.page.workbench'],
          featureCode: 'menu.discovery.workbench',
          icon: 'lucide:layout-dashboard',
          keepAlive: true,
          order: 5,
          tabGroup: DISCOVERY_WORKBENCH_TAB_GROUP,
          title: '项目工作台',
        },
      },
    ],
  },
];

export default routes;
