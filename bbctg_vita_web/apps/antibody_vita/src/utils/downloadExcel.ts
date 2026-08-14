import { ElLoading, ElMessage } from 'element-plus';

const XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

export function excelTimestamp() {
  return new Date(Date.now() + 8 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 16)
    .replace('T', '_')
    .replace(':', '');
}

export async function downloadListExcel(
  request: () => Promise<Blob>,
  fallbackName: string,
) {
  const loading = ElLoading.service({
    lock: true,
    text: '正在导出数据...',
    background: 'rgba(0, 0, 0, 0.7)',
  });
  try {
    const response = await request();
    const blob = response instanceof Blob
      ? response
      : new Blob([response], { type: XLSX_TYPE });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fallbackName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success('导出成功');
  } finally {
    loading.close();
  }
}
