import type { RouteRecordRaw } from 'vue-router';

const DISCOVERY_WORKBENCH_TAB_GROUP = '/discovery/workbench';
const DISCOVERY_SYNTHESIS_TAB_GROUP = '/discovery/synthesis-progress';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['discovery.page.workbench', 'discovery.page.synthesis_progress'],
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
          fullPathKey: false,
          icon: 'lucide:layout-dashboard',
          keepAlive: true,
          order: 5,
          tabGroup: DISCOVERY_WORKBENCH_TAB_GROUP,
          menuTitle: '项目工作台',
          title: '发现工作台',
        },
      },
      {
        name: 'DiscoverySynthesisProgress',
        path: '/discovery/synthesis-progress',
        component: () => import('#/views/Discovery/synthesis/SynthesisProgress.vue'),
        meta: {
          authority: ['discovery.page.synthesis_progress'],
          featureCode: 'menu.discovery.synthesis_progress',
          fullPathKey: false,
          icon: 'lucide:list-checks',
          keepAlive: true,
          order: 10,
          tabGroup: DISCOVERY_SYNTHESIS_TAB_GROUP,
          title: '合成与验证',
        },
      },
    ],
  },
];

export default routes;
