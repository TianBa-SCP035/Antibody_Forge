export type SerumProjectStatusTagType =
  | 'danger'
  | 'info'
  | 'primary'
  | 'success'
  | 'warning';

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
