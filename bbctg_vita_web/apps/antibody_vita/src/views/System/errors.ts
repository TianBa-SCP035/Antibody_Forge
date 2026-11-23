import type { OperationMessages } from '#/api/errors';

export const SYSTEM_ERRORS = {
  loadData: {
    default: '用户权限数据加载失败',
  } satisfies OperationMessages,
  loadFeatures: {
    default: '系统功能配置加载失败',
  } satisfies OperationMessages,
  loadOverride: {
    default: '个人权限加载失败',
  } satisfies OperationMessages,
  saveFeature: {
    default: '系统功能配置保存失败',
  } satisfies OperationMessages,
  savePassword: {
    default: '密码保存失败',
  } satisfies OperationMessages,
  saveProfile: {
    default: '保存失败',
  } satisfies OperationMessages,
} as const;
