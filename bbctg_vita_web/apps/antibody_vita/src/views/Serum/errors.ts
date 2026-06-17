import type { OperationMessages } from '#/api/errors';

export const SERUM_ERRORS = {
  cell: {
    load: {
      default: '细胞库存数据加载失败',
      network: '网络请求失败，请检查连接',
    } satisfies OperationMessages,
    updatePrepStatus: {
      default: '制备状态更新失败',
    } satisfies OperationMessages,
  },
  detail: {
    exportPdf: {
      default: '打印失败，请稍后重试',
    } satisfies OperationMessages,
    exportScheme: {
      default: '导出失败，请稍后重试',
    } satisfies OperationMessages,
  },
  edit: {
    autoSave: {
      default: '自动保存失败',
      timeout: '保存超时，请重试',
    } satisfies OperationMessages,
    delete: {
      default: '删除失败',
    } satisfies OperationMessages,
    loadPage: {
      default: '页面数据加载失败',
    } satisfies OperationMessages,
    nextId: {
      default: '获取实验 ID 失败',
      timeout: '获取实验 ID 超时，请重试',
    } satisfies OperationMessages,
    save: {
      default: '保存失败',
      timeout: '保存超时，请重试',
    } satisfies OperationMessages,
  },
  list: {
    autoUpdateStatus: {
      default: '状态更新失败，请重试',
    } satisfies OperationMessages,
    exportMouse: {
      default: '导出失败，请重试',
    } satisfies OperationMessages,
    initMeta: {
      default: '列表数据加载失败',
    } satisfies OperationMessages,
    loadList: {
      default: '列表加载失败',
    } satisfies OperationMessages,
    updateCage: {
      default: '笼位更新失败',
      errorCodes: {
        SERUM_CAGE_NO_MOUSE: {
          level: 'warning',
          message: '鼠鼠不存在',
        },
      },
    } satisfies OperationMessages,
    updateStatus: {
      default: '状态修改失败',
    } satisfies OperationMessages,
  },
  titer: {
    deleteFile: {
      default: '删除附件失败',
    } satisfies OperationMessages,
    deletePlate: {
      default: '删除失败',
    } satisfies OperationMessages,
    download: {
      default: '下载失败',
      forbidden: '没有权限下载此文件',
      notFound: '文件不存在',
    } satisfies OperationMessages,
    load: {
      default: '效价数据加载失败',
    } satisfies OperationMessages,
    savePlate: {
      default: '保存失败',
    } satisfies OperationMessages,
    upload: {
      default: '上传失败',
    } satisfies OperationMessages,
    rename: {
      default: '重命名失败',
    } satisfies OperationMessages,
    replace: {
      default: '替换失败',
    } satisfies OperationMessages,
  },
} as const;
