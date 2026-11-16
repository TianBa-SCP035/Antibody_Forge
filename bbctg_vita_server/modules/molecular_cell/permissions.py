from core.module_spec import ModuleAccess, action, menu, page

ACCESS = ModuleAccess(
    module="molecular",
    permissions=(
        page("molecular.page.library", "文库构建", resource="library", route_path="/molecular-cell/library-construction",
             sort_order=430, message="没有权限访问文库构建"),
        action("molecular.library.edit", "编辑文库构建工单", resource="library", action="edit",
               ui_key="molecular.library.edit_button", parent_code="molecular.page.library", sort_order=431,
               message="没有权限编辑文库构建工单"),
        page("molecular.page.library_detail", "文库构建详情", resource="library_detail",
             route_path="/molecular-cell/library-construction/result", parent_code="molecular.page.library",
             sort_order=433, message="没有权限查看文库构建详情"),
        action("molecular.library.file.manage", "管理质检文件和结论", resource="library_file", action="manage",
               ui_key="molecular.library.file.manage_button", parent_code="molecular.page.library_detail",
               sort_order=434, message="没有权限管理文库质检"),
        page("molecular.page.primer", "引物库", resource="primer", route_path="/molecular-cell/primer-library",
             sort_order=440, message="没有权限访问引物库"),
        action("molecular.primer.edit", "编辑引物库", resource="primer", action="edit",
               ui_key="molecular.primer.edit_button", parent_code="molecular.page.primer", sort_order=441,
               message="没有权限编辑引物库"),
    ),
    resources={"library": "文库工单", "library_detail": "文库工单", "library_file": "构建文件", "primer": "引物库"},
    features=(
        menu("menu.molecular_cell", "分子与细胞", "控制分子与细胞模块菜单显示", sort_order=30, path="/molecular-cell",
             icon="lucide:dna"),
        menu("menu.molecular_cell.library", "文库构建", "控制文库构建页面显示", sort_order=10,
             path="/molecular-cell/library-construction", icon="lucide:library", parent_code="menu.molecular_cell"),
        menu("menu.molecular_cell.primer", "引物库", "控制引物库页面显示", sort_order=5,
             path="/molecular-cell/primer-library", icon="lucide:flask-conical", parent_code="menu.molecular_cell"),
    ),
)
