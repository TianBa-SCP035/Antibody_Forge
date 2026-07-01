import type { RouteRecordRaw } from 'vue-router';

const SERUM_TAB_GROUP = '/serum';
const SERUM_TITER_ORDER_TAB_GROUP = '/serum/titer-orders';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:test-tube',
      featureCode: 'menu.serum',
      order: 10,
      title: '小鼠免疫',
    },
    name: 'Serum',
    path: '/serum',
    redirect: '/serum/list',
    children: [
      {
        name: 'SerumList',
        path: '/serum/list',
        component: () => import('#/views/Serum/SerumList.vue'),
        meta: {
          authority: ['serum.page.list'],
          icon: 'lucide:list',
          keepAlive: true,
          tabGroup: SERUM_TAB_GROUP,
          title: '免疫实验列表',
        },
      },
      {
        name: 'SerumDataDetail',
        path: '/serum/detail',
        component: () => import('#/views/Serum/SerumDataDetail.vue'),
        meta: {
          authority: ['serum.page.detail'],
          hideInMenu: true,
          icon: 'lucide:file-text',
          keepAlive: true,
          tabGroup: SERUM_TAB_GROUP,
          title: '免疫实验详情',
        },
      },
      {
        name: 'SerumTiterOrderList',
        path: '/serum/titer-orders',
        component: () => import('#/views/Serum/SerumTiterOrderList.vue'),
        meta: {
          authority: ['serum.page.titer_order'],
          icon: 'lucide:clipboard-list',
          keepAlive: true,
          tabGroup: SERUM_TITER_ORDER_TAB_GROUP,
          title: '效价实验列表',
        },
      },
      {
        name: 'SerumEdit',
        path: '/serum/edit',
        component: () => import('#/views/Serum/SerumEdit.vue'),
        meta: {
          authority: ['serum.page.edit'],
          hideInMenu: true,
          icon: 'lucide:edit',
          keepAlive: true,
          tabGroup: SERUM_TAB_GROUP,
          title: '编辑免疫实验',
        },
      },
      {
        name: 'SerumTiter',
        path: '/serum/titer',
        component: () => import('#/views/Serum/SerumTiter.vue'),
        meta: {
          authority: ['serum.page.titer'],
          hideInMenu: true,
          icon: 'lucide:chart-no-axes-combined',
          keepAlive: true,
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
          tabGroup: SERUM_TAB_GROUP,
          title: '细胞及库存管理',
        },
      },
    ],
  },
];

export default routes;
