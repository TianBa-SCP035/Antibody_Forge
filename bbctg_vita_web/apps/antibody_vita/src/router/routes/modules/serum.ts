import type { RouteRecordRaw } from 'vue-router';

const SERUM_TAB_GROUP = '/serum';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:test-tube',
      order: 10,
      title: '血清实验',
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
          title: '血清实验列表',
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
          title: '血清实验详情',
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
          title: '编辑血清实验',
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
          title: '血清效价数据',
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
          title: '细胞库存查询',
        },
      },
    ],
  },
];

export default routes;
