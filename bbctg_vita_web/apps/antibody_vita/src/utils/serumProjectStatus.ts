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
  if (priority === '加急') return 'warning';
  if (priority === '非常紧急') return 'danger';
  if (priority === '吉吉国王') return 'king';
  return 'info';
}
