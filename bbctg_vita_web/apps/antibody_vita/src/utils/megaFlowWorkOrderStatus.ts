const ORDER_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  validated: '已校验',
  sent: '已发送',
  running: '执行中',
  paused: '已暂停',
  pausing: '暂停中',
  resuming: '恢复中',
  execution_failed: '执行失败',
  completed: '已完成',
  failed: '校验失败',
  cancelled: '已作废',
};

const DISPATCH_STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  running: '执行中',
  completed: '完成',
  failed: '失败',
  voided: '作废',
};

const DISPATCH_PAUSE_STATE_LABELS: Record<string, string> = {
  pausing: '暂停中',
  paused: '已暂停',
  resuming: '恢复中',
};

export function resolveOrderDisplayLabel(order: {
  status?: string;
  display_status_label?: string;
  pause_state?: string;
}) {
  if (order.display_status_label) return order.display_status_label;
  if (order.status === 'paused') {
    const pause = String(order.pause_state || '').trim();
    if (pause === 'pausing') return '暂停中';
    if (pause === 'resuming') return '恢复中';
    return '已暂停';
  }
  return ORDER_STATUS_LABELS[order.status || ''] || order.status || '-';
}

export function resolveOrderDisplayStatus(order: {
  status?: string;
  display_status?: string;
  pause_state?: string;
}) {
  if (order.display_status) return order.display_status;
  if (order.status === 'paused') {
    const pause = String(order.pause_state || '').trim();
    if (pause === 'pausing') return 'pausing';
    if (pause === 'resuming') return 'resuming';
    return 'paused';
  }
  return order.status || '';
}

export function orderStatusTagType(displayStatus: string) {
  if (displayStatus === 'failed' || displayStatus === 'execution_failed') return 'danger';
  if (displayStatus === 'sent' || displayStatus === 'running' || displayStatus === 'completed') {
    return 'success';
  }
  if (displayStatus === 'pausing' || displayStatus === 'paused' || displayStatus === 'resuming') {
    return 'warning';
  }
  if (displayStatus === 'cancelled') return 'info';
  return 'primary';
}

function dispatchStatusLabel(status?: string) {
  return DISPATCH_STATUS_LABELS[String(status || '').trim()] || status || '-';
}

function dispatchPauseStateLabel(pauseState?: string) {
  const normalized = String(pauseState || '').trim();
  return DISPATCH_PAUSE_STATE_LABELS[normalized] || '';
}

export function buildDispatchChipLabel(item: {
  dispatchId?: string;
  status?: string;
  pause_state?: string;
}) {
  const parts = [item.dispatchId, dispatchStatusLabel(item.status)];
  const pauseLabel = dispatchPauseStateLabel(item.pause_state);
  if (pauseLabel) parts.push(pauseLabel);
  return parts.filter(Boolean).join(' · ');
}

export function normalizePauseState(pauseState?: string) {
  return String(pauseState || '').trim();
}
