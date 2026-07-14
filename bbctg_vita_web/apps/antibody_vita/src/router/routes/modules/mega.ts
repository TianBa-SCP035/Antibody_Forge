import type { RouteRecordRaw } from 'vue-router';

const MEGA_FLOW_ORDER_TAB_GROUP = '/mega-automation/flow-work-orders';

const routes: RouteRecordRaw[] = [
  {
    name: 'MegaAutomation',
    path: '/mega-automation',
    redirect: '/mega-automation/flow-work-orders',
    meta: {
      authority: ['mega.page.flow_work_order'],
      featureCode: 'menu.mega_automation',
      icon: 'lucide:workflow',
      order: 50,
      title: '镁伽自动化',
    },
    children: [
      {
        name: 'MegaFlowWorkOrderList',
        path: '/mega-automation/flow-work-orders',
        component: () =>
          import('#/views/MegaAutomation/FlowWorkOrder/FlowWorkOrderList.vue'),
        meta: {
          authority: ['mega.page.flow_work_order'],
          featureCode: 'menu.mega_automation.flow_work_orders',
          icon: 'lucide:clipboard-list',
          keepAlive: true,
          tabGroup: MEGA_FLOW_ORDER_TAB_GROUP,
          title: '流式工单总览',
        },
      },
      {
        name: 'MegaFlowWorkOrderDetail',
        path: '/mega-automation/flow-work-orders/detail',
        component: () =>
          import('#/views/MegaAutomation/FlowWorkOrder/FlowWorkOrderDetail.vue'),
        meta: {
          authority: ['mega.page.flow_work_order'],
          hideInMenu: true,
          icon: 'lucide:file-text',
          // 同一详情页 query.id 变化不应拆成多个 KeepAlive 实例，否则首次保存
          // replace 写入 id 会整页重挂载并再次全屏 loadDetail。
          fullPathKey: false,
          keepAlive: true,
          tabGroup: MEGA_FLOW_ORDER_TAB_GROUP,
          title: '流式工单详情',
        },
      },
    ],
  },
];

export default routes;
