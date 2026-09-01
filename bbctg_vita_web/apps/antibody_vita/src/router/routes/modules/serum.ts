import type { RouteRecordRaw } from 'vue-router';

const SERUM_TAB_GROUP = '/serum';
const SERUM_WORKBENCH_TAB_GROUP = '/serum/workbench';
const SERUM_TITER_ORDER_TAB_GROUP = '/serum/titer-orders';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:test-tube',
      featureCode: 'menu.serum',
      order: 10,
      title: '小鼠免疫',
      authority: ['serum.page.workbench', 'serum.page.list', 'serum.page.titer_order'],
    },
    name: 'Serum',
    path: '/serum',
    children: [
      {
        name: 'SerumWorkbench',
        path: '/serum/workbench',
        component: () => import('#/views/Serum/workbench/SerumWorkbench.vue'),
        meta: {
          authority: ['serum.page.workbench'],
          featureCode: 'menu.serum.workbench',
          icon: 'lucide:layout-dashboard',
          keepAlive: true,
          order: 5,
          tabGroup: SERUM_WORKBENCH_TAB_GROUP,
          title: '项目工作台',
        },
      },
      {
        name: 'SerumList',
        path: '/serum/list',
        component: () => import('#/views/Serum/immune/SerumList.vue'),
        meta: {
          authority: ['serum.page.list'],
          featureCode: 'menu.serum.list',
          icon: 'lucide:list',
          keepAlive: true,
          order: 10,
          tabGroup: SERUM_TAB_GROUP,
          title: '免疫实验列表',
        },
      },
      {
        name: 'SerumDataDetail',
        path: '/serum/detail',
        component: () => import('#/views/Serum/immune/SerumDataDetail.vue'),
        meta: {
          authority: ['serum.page.detail'],
          hideInMenu: true,
          icon: 'lucide:file-text',
          keepAlive: true,
          activePath: '/serum/list',
          tabGroup: SERUM_TAB_GROUP,
          title: '免疫实验详情',
        },
      },
      {
        name: 'SerumTiterOrderList',
        path: '/serum/titer-orders',
        component: () => import('#/views/Serum/titer/SerumTiterOrderList.vue'),
        meta: {
          authority: ['serum.page.titer_order'],
          featureCode: 'menu.serum.titer_order',
          icon: 'lucide:clipboard-list',
          keepAlive: true,
          tabGroup: SERUM_TITER_ORDER_TAB_GROUP,
          title: '效价实验列表',
        },
      },
      {
        name: 'SerumWorkbenchScheme',
        path: '/serum/workbench/scheme',
        component: () => import('#/views/Serum/workbench/SerumWorkbenchScheme.vue'),
        meta: {
          authority: ['serum.page.workbench'],
          hideInMenu: true,
          icon: 'lucide:file-pen',
          // 不按 query.id 拆 KeepAlive 实例；同一方案页切记录时由页面主动重载。
          fullPathKey: false,
          keepAlive: true,
          activePath: '/serum/workbench',
          tabGroup: SERUM_WORKBENCH_TAB_GROUP,
          title: '方案草稿',
        },
      },
      {
        name: 'SerumEdit',
        path: '/serum/edit',
        component: () => import('#/views/Serum/immune/SerumEdit.vue'),
        meta: {
          authority: ['serum.page.edit'],
          hideInMenu: true,
          icon: 'lucide:edit',
          fullPathKey: false,
          keepAlive: true,
          activePath: '/serum/list',
          tabGroup: SERUM_TAB_GROUP,
          title: '编辑免疫实验',
        },
      },
      {
        name: 'SerumTiter',
        path: '/serum/titer',
        component: () => import('#/views/Serum/titer/SerumTiter.vue'),
        meta: {
          authority: ['serum.page.titer'],
          hideInMenu: true,
          icon: 'lucide:chart-no-axes-combined',
          keepAlive: true,
          activePath: '/serum/list',
          tabGroup: SERUM_TAB_GROUP,
          title: '效价数据',
        },
      },
      {
        name: 'SerumCell',
        path: '/serum/cell',
        component: () => import('#/views/Serum/SerumCell.vue'),
        meta: {
          authority: ['serum.page.cell'],
          hideInMenu: true,
          icon: 'lucide:warehouse',
          keepAlive: true,
          activePath: '/serum/list',
          tabGroup: SERUM_TAB_GROUP,
          title: '细胞及库存管理',
        },
      },
    ],
  },
];

export default routes;
