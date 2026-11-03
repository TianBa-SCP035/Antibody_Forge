/** 表格里不弹浏览器右键菜单；输入框里和右键点在选中文字上时保留，方便粘贴、复制、翻译。 */
export function initTableContextMenu() {
  document.addEventListener('contextmenu', (event) => {
    const target = event.target;
    if (!(target instanceof Element) || !target.closest('.el-table, .vxe-table')) return;
    if (target.closest('input, textarea')) return;
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed && selection.containsNode(target, true)) return;
    event.preventDefault();
  });
}
