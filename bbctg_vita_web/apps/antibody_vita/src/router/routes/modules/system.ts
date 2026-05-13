import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    name: 'SystemManagement',
    path: '/system',
    component: () => import('#/views/System/SystemManagement.vue'),
    meta: {
      authority: [
        'system.page.user',
        'system.page.role',
        'system.page.permission',
        'system.page.operation_log',
      ],
      icon: 'lucide:settings',
      order: 90,
      tabGroup: '/system',
      title: '系统管理',
    },
  },
];

export default routes;
