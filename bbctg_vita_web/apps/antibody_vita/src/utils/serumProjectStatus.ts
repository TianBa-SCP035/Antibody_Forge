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
