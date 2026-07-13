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
          keepAlive: true,
          tabGroup: MEGA_FLOW_ORDER_TAB_GROUP,
          title: '流式工单详情',
        },
      },
    ],
  },
];

export default routes;
