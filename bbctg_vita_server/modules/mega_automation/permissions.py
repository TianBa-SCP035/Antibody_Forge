from core.module_spec import ModuleAccess, action, job, menu, page

ACCESS = ModuleAccess(
    module="mega",
    permissions=(
        page("mega.page.flow_work_order", "流式工单总览", resource="flow_work_order",
             route_path="/mega-automation/flow-work-orders", sort_order=500, message="没有权限查看流式工单总览"),
        action("mega.flow_work_order.edit", "编辑流式工单", resource="flow_work_order", action="edit",
               ui_key="mega.flow_work_order.edit_button", parent_code="mega.page.flow_work_order", sort_order=510,
               message="没有权限编辑流式工单"),
        action("mega.flow_work_order.dispatch", "发送流式工单", resource="flow_work_order", action="dispatch",
               ui_key="mega.flow_work_order.dispatch_button", parent_code="mega.page.flow_work_order",
               sort_order=520, message="没有权限发送流式工单"),
    ),
    resources={"flow_work_order": "流式工单"},
    features=(
        menu("menu.mega_automation", "镁伽自动化菜单", "控制镁伽自动化模块菜单显示", sort_order=50,
             path="/mega-automation", icon="lucide:workflow"),
        menu("menu.mega_automation.flow_work_orders", "流式工单总览", "控制流式工单总览页面显示", sort_order=10,
             path="/mega-automation/flow-work-orders", icon="lucide:clipboard-list",
             parent_code="menu.mega_automation"),
        job("job.mega_labillion_status_sync", "镁伽工单状态同步", "同步镁伽非终态工单状态", sort_order=220, hour=2,
            minute=0),
    ),
)
