import type { RouteRecordRaw } from 'vue-router';

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
          icon: 'lucide:list',
          title: '血清实验列表',
        },
      },
      {
        name: 'SerumDataDetail',
        path: '/serum/detail',
        component: () => import('#/views/Serum/SerumDataDetail.vue'),
        meta: {
          hideInMenu: true,
          icon: 'lucide:file-text',
          title: '血清实验详情',
        },
      },
      {
        name: 'SerumEdit',
        path: '/serum/edit',
        component: () => import('#/views/Serum/SerumEdit.vue'),
        meta: {
          hideInMenu: true,
          icon: 'lucide:edit',
          title: '编辑血清实验',
        },
      },
      {
        name: 'SerumTiter',
        path: '/serum/titer',
        component: () => import('#/views/Serum/SerumTiter.vue'),
        meta: {
          hideInMenu: true,
          icon: 'lucide:chart-no-axes-combined',
          title: '血清效价数据',
        },
      },
      {
        name: 'SerumCell',
        path: '/serum/cell',
        component: () => import('#/views/Serum/SerumCell.vue'),
        meta: {
          hideInMenu: true,
          icon: 'lucide:warehouse',
          title: '细胞库存查询',
        },
      },
    ],
  },
];

export default routes;
