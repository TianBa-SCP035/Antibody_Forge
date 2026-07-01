import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/system',
    redirect: '/system/user-permission',
    meta: {
      // 与任一子页权限一致：父级未设 authority 时前端会视为全员可见，导致子级全被过滤后仍显示「系统管理」空目录
      authority: [
        'system.page.user',
        'system.page.role',
        'system.page.permission',
        'system.page.operation_log',
        'system.page.feature',
      ],
      featureCode: 'menu.system',
      icon: 'lucide:settings',
      order: 90,
      title: '系统管理',
    },
    name: 'System',
    children: [
      {
        name: 'SystemUserPermission',
        path: '/system/user-permission',
        component: () => import('#/views/System/SystemManagement.vue'),
        meta: {
          authority: [
            'system.page.user',
            'system.page.role',
            'system.page.permission',
            'system.page.operation_log',
          ],
          featureCode: 'menu.system.user_permission',
          icon: 'lucide:shield-check',
          keepAlive: true,
          tabGroup: '/system',
          title: '用户权限',
        },
      },
      {
        name: 'SystemFeatures',
        path: '/system/features',
        component: () => import('#/views/System/SystemFeatures.vue'),
        meta: {
          authority: ['system.page.feature'],
          featureCode: 'menu.system.features',
          icon: 'lucide:sliders-horizontal',
          keepAlive: true,
          tabGroup: '/system',
          title: '系统功能',
        },
      },
    ],
  },
];

export default routes;
