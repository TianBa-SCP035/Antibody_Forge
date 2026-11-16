from core.module_spec import ModuleAccess, job, menu, page

ACCESS = ModuleAccess(
    module="atlas",
    permissions=(
        page("atlas.page.target_library", "靶点情报", resource="target", route_path="/atlas/targets", sort_order=50,
             message="没有权限查看靶点情报"),
    ),
    resources={"target": "靶点"},
    features=(
        menu("menu.atlas", "千鼠万抗", "控制千鼠万抗父级菜单显示", sort_order=5, path="/atlas", icon="lucide:network"),
        menu("menu.atlas.target_library", "靶点情报", "控制靶点情报页面显示", sort_order=10, path="/atlas/targets",
             icon="lucide:database", parent_code="menu.atlas"),
        job("job.target_master_sync", "靶点主数据定时同步", "同步外部靶点主数据", sort_order=205, hour=0, minute=45),
    ),
)
