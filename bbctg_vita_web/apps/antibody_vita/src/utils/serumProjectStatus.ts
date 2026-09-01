export type SerumProjectStatusTagType =
  | 'danger'
  | 'info'
  | 'primary'
  | 'success'
  | 'warning';

export type TiterPriorityTone = SerumProjectStatusTagType | 'king';

/** 效价工单血清状态下拉选项，从低到高。 */
export const TITER_SERUM_STATUS_OPTIONS = [
  '待采血',
  '待采血-加免',
  '已采血',
  '已检测',
  '已交接',
  '已销毁',
] as const;

/** 检测优先级，从低到高。建单默认「正常」。 */
export const TITER_PRIORITY_OPTIONS = ['正常', '加急', '非常紧急', '吉吉国王'] as const;

export const TITER_PRIORITY_DEFAULT = '正常';

export const SERUM_PROJECT_STATUS_OPTIONS = [
  '规划中',
  '待一免',
  '待二免',
  '待三免',
  '待四免',
  '待五免',
  '待六免',
  '加免中',
  '待检测',
  '待上机',
  '已采血',
  '已上传',
  '已检测',
  '已汇报',
  '无效价处死',
  '结题',
] as const;
export const SERUM_PROJECT_STATUS_DEFAULT = SERUM_PROJECT_STATUS_OPTIONS[0];

/** 固定默认项在前，再按字母序追加接口返回的其它状态。 */
export function mergeTiterSerumStatusOptions(
  fromApi: string[] | null | undefined,
): string[] {
  const seen = new Set<string>();
  const merged: string[] = [];
  for (const status of TITER_SERUM_STATUS_OPTIONS) {
    if (!seen.has(status)) {
      merged.push(status);
      seen.add(status);
    }
  }
  for (const status of [...(fromApi || [])].sort()) {
    const value = String(status || '').trim();
    if (value && !seen.has(value)) {
      merged.push(value);
      seen.add(value);
    }
  }
  return merged;
}

/** Element Plus el-tag type for serum project_status display. */
export function getSerumProjectStatusTagType(
  status: string | null | undefined,
): SerumProjectStatusTagType {
  if (!status) return 'info';
  if (status === '无效价处死') return 'danger';
  if (status.startsWith('待') || status === '加免中') return 'primary';
  if (status === '结题') return 'success';
  if (status.startsWith('已')) return 'warning';
  return 'info';
}

/** Element Plus el-tag type for titer order serum_status display. */
export function getSerumTiterStatusTagType(
  status: string | null | undefined,
): SerumProjectStatusTagType {
  if (!status) return 'info';
  if (status === '已销毁') return 'danger';
  if (status === '已交接') return 'success';
  if (status === '已检测') return 'warning';
  if (status === '已采血') return 'primary';
  if (status.startsWith('待采血')) return 'info';
  return 'info';
}

/** 检测优先级色：正常灰 → 加急橙 → 非常紧急红 → 吉吉国王紫。 */
export function getTiterPriorityTone(
  priority: string | null | undefined,
): TiterPriorityTone {
  const value = canonicalizeWorkbenchPriority(priority);
  if (value === '加急') return 'warning';
  if (value === '非常紧急') return 'danger';
  if (value === '吉吉国王') return 'king';
  return 'info';
}

/** 工作台优先级与效价实验列表使用同一组选项。 */
export const WORKBENCH_PRIORITY_OPTIONS = TITER_PRIORITY_OPTIONS;
export const WORKBENCH_PRIORITY_DEFAULT = TITER_PRIORITY_DEFAULT;

export function canonicalizeWorkbenchPriority(priority: string | null | undefined): string {
  return String(priority || '').trim() || WORKBENCH_PRIORITY_DEFAULT;
}

/** 未开展工作台状态选项；已开展后展示实验表状态。 */
export const WORKBENCH_CLOSED_PLAN_STATUSES = [
  '小鼠KO致死',
  '已取消',
] as const;

export const WORKBENCH_PLAN_STATUS_OPTIONS = [
  '草稿',
  '筹备中',
  ...WORKBENCH_CLOSED_PLAN_STATUSES,
] as const;

export function isWorkbenchPlanClosed(status: string | null | undefined): boolean {
  return WORKBENCH_CLOSED_PLAN_STATUSES.some((item) => item === status);
}

export function getWorkbenchPlanStatusTagType(
  status: string | null | undefined,
): SerumProjectStatusTagType {
  if (!status) return 'info';
  if (status === '小鼠KO致死') return 'danger';
  if (status === '筹备中') return 'primary';
  if (status === '已开展') return 'success';
  if (status.includes('取消')) return 'info';
  return 'info';
}

export function getWorkbenchDisplayStatusTagType(
  row: { aligned_locked?: boolean; display_status?: string | null; plan_status?: string | null },
): SerumProjectStatusTagType {
  const status = row.display_status || row.plan_status;
  if (row.aligned_locked) return getSerumProjectStatusTagType(status);
  return getWorkbenchPlanStatusTagType(status);
}
