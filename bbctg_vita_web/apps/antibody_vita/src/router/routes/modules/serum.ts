import type { RouteRecordRaw } from 'vue-router';

const SERUM_TAB_GROUP = '/serum';

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
          tabGroup: SERUM_TAB_GROUP,
          title: '免疫实验详情',
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
          tabGroup: SERUM_TAB_GROUP,
          title: '细胞及库存管理',
        },
      },
    ],
  },
];

export default routes;
