/** 镁伽结果回传的状态文案与标签颜色，回传记录页和工单详情「回传结果」共用。 */

type TagType = 'danger' | 'info' | 'primary' | 'success' | 'warning';

interface StatusOption {
  label: string;
  tag: TagType;
  value: string;
}

export const SYNC_STATUS_OPTIONS: StatusOption[] = [
  { value: 'passed', label: '全部通过', tag: 'success' },
  { value: 'partial', label: '部分通过', tag: 'warning' },
  { value: 'rejected', label: '全部未通过', tag: 'danger' },
  { value: 'invalid', label: '格式错误', tag: 'danger' },
  { value: 'error', label: '处理异常', tag: 'danger' },
];

export const SYNC_IMPORT_OPTIONS: StatusOption[] = [
  { value: 'pending', label: '待导入', tag: 'info' },
  { value: 'running', label: '导入中', tag: 'primary' },
  { value: 'done', label: '已完成', tag: 'success' },
  { value: 'failed', label: '有失败', tag: 'danger' },
  { value: 'none', label: '无需导入', tag: 'info' },
];

const BOARD_VERIFY_OPTIONS: StatusOption[] = [
  { value: 'passed', label: '通过', tag: 'success' },
  { value: 'rejected', label: '未通过', tag: 'danger' },
  { value: 'archived', label: '仅存档', tag: 'info' },
];

const BOARD_IMPORT_OPTIONS: StatusOption[] = [
  { value: 'none', label: '不导入', tag: 'info' },
  { value: 'pending', label: '待导入', tag: 'info' },
  { value: 'done', label: '已导入', tag: 'success' },
  { value: 'skipped', label: '未覆盖', tag: 'warning' },
  { value: 'download_failed', label: '下载失败', tag: 'danger' },
  { value: 'failed', label: '导入失败', tag: 'danger' },
];

function find(options: StatusOption[], value: null | string | undefined) {
  return options.find((item) => item.value === value);
}

export function syncStatusLabel(value: null | string | undefined) {
  return find(SYNC_STATUS_OPTIONS, value)?.label || value || '—';
}

export function syncStatusTag(value: null | string | undefined): TagType {
  return find(SYNC_STATUS_OPTIONS, value)?.tag || 'info';
}

export function syncImportLabel(value: null | string | undefined) {
  return find(SYNC_IMPORT_OPTIONS, value)?.label || value || '—';
}

export function syncImportTag(value: null | string | undefined): TagType {
  return find(SYNC_IMPORT_OPTIONS, value)?.tag || 'info';
}

export function boardVerifyLabel(value: null | string | undefined) {
  return find(BOARD_VERIFY_OPTIONS, value)?.label || value || '—';
}

export function boardVerifyTag(value: null | string | undefined): TagType {
  return find(BOARD_VERIFY_OPTIONS, value)?.tag || 'info';
}

export function boardImportLabel(value: null | string | undefined) {
  return find(BOARD_IMPORT_OPTIONS, value)?.label || value || '—';
}

export function boardImportTag(value: null | string | undefined): TagType {
  return find(BOARD_IMPORT_OPTIONS, value)?.tag || 'info';
}
