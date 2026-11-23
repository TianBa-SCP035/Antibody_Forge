import { ElMessage } from 'element-plus'

import { notifyApiError } from '#/api/errors'
import { fetchSerumDetailByExperimentId } from '#/api/serum'

/**
 * 按实验号跳到免疫项目详情。vm 是工作台页面：要有 canViewSerumProject、flushEditorForAction(row)、$router。
 * code 为空时提示 emptyMessage（各页让用户填的字段不同）。
 */
export async function openSerumProject(vm, row, code, emptyMessage) {
  if (!vm.canViewSerumProject) {
    ElMessage.warning('您没有免疫实验详情权限')
    return
  }
  if (!code) {
    ElMessage.warning(emptyMessage)
    return
  }
  if (!await vm.flushEditorForAction(row)) return
  try {
    const detail = await fetchSerumDetailByExperimentId(code)
    const projectId = Number(detail?.id)
    if (!Number.isSafeInteger(projectId) || projectId <= 0) {
      ElMessage.warning('未找到对应的免疫项目')
      return
    }
    vm.$router.push({ path: '/serum/detail', query: { id: projectId } })
  } catch (error) {
    notifyApiError(error, { messages: { default: '未找到对应的免疫项目' } })
  }
}
