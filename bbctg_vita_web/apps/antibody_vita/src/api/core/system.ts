import { requestClient } from '#/api/request';

export interface SystemUser {
  id?: number;
  username: string;
  display_name?: string;
  openid?: string;
  job_no?: string;
  department?: string;
  group_name?: string;
  position_title?: string;
  gender?: string;
  profile_signature?: string;
  employment_status?: string;
  email?: string;
  mobile?: string;
  status?: string;
  is_superuser?: boolean;
  role_ids?: number[];
}

export interface SystemRole {
  id?: number;
  code: string;
  name: string;
  description?: string;
  status?: string;
  sort_order?: number;
  bundle_codes?: string[];
  permission_codes?: string[];
}

export interface SystemPermission {
  id: number;
  code: string;
  name: string;
  type: string;
  action?: string;
  module?: string;
  parent_code?: string;
  resource?: string;
  route_path?: string;
  description?: string;
  sort_order: number;
  status: string;
  ui_key?: string;
}

export interface SystemPermissionBundle {
  id?: number;
  code: string;
  name: string;
  module: string;
  description?: string;
  status?: string;
  sort_order?: number;
  permission_codes: string[];
}

export interface SystemPermissionOverride {
  id?: number;
  user_id: number;
  permission_code: string;
  effect: 'allow' | 'deny';
  reason?: string;
}

export interface SystemUserPermissionOverrides {
  user: SystemUser;
  role_permissions: string[];
  effective_permissions: string[];
  overrides: SystemPermissionOverride[];
}

export interface SystemOperationLogQuery {
  action?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  result?: string;
  username?: string;
}

export interface SystemOperationLog {
  action: string;
  created_at?: string;
  detail?: Record<string, any>;
  error_message?: string;
  id: number;
  operation_name?: string;
  operation_type?: string;
  operator_name?: string;
  result: string;
  target_id?: string;
  target_label?: string;
  target_type?: string;
  user_id?: number;
  username?: string;
}

export interface SystemAuditTargetSnapshot {
  code?: string;
  display_name?: string;
  name?: string;
  target_label?: string;
  username?: string;
}

export interface SystemFeatureFlag {
  category: 'feature' | 'job' | 'menu' | string;
  code: string;
  config?: Record<string, any>;
  description?: string;
  enabled: boolean;
  id?: number;
  name: string;
  sort_order?: number;
  visible: boolean;
}

export interface SystemJobRunLog {
  detail?: Record<string, any>;
  duration_ms?: number;
  error_message?: string;
  finished_at?: string;
  id: number;
  job_code: string;
  job_name: string;
  result: string;
  started_at?: string;
  summary?: string;
}

export interface SystemUserQuery {
  department?: string;
  employment_status?: string;
  gender?: string;
  group_name?: string;
  has_admin_role?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  status?: string;
}

export function getSystemUsersApi(params: string | SystemUserQuery = '') {
  const query = typeof params === 'string' ? { keyword: params } : params;
  return requestClient.get<{
    active_total?: number;
    items: SystemUser[];
    page?: number;
    page_size?: number;
    total?: number;
  }>('/system/users', {
    params: query,
  });
}

export function getSystemUserSuggestionsApi(params: {
  field: 'department' | 'group_name' | 'keyword';
  keyword?: string;
  limit?: number;
}) {
  return requestClient.get<{ items: string[] }>('/system/users/suggestions', {
    params,
  });
}

export function saveSystemUserApi(data: SystemUser & { password?: string }) {
  return requestClient.post('/system/users/save', data);
}

export function getSystemFeaturesApi() {
  return requestClient.get<{ items: SystemFeatureFlag[] }>('/system/features');
}

export function getSystemEffectiveFeaturesApi() {
  return requestClient.get<{
    items: Array<Pick<SystemFeatureFlag, 'category' | 'code' | 'enabled' | 'sort_order' | 'visible'>>;
  }>('/system/features/effective');
}

export function getSystemJobRunLogsApi(
  params: {
    end_date?: string;
    job_code?: string;
    limit?: number;
    result?: string;
    start_date?: string;
  } = {},
) {
  return requestClient.get<{ items: SystemJobRunLog[] }>('/system/features/job_logs', {
    params,
  });
}

export function getSystemFeatureStatusApi() {
  return requestClient.get<{
    server_time: string;
    timezone: string;
    user_id?: number;
  }>('/system/features/system_status');
}

export function saveSystemFeatureApi(data: SystemFeatureFlag) {
  return requestClient.post<SystemFeatureFlag>('/system/features/save', data);
}

export function deleteSystemUserApi(id: number, snapshot: SystemAuditTargetSnapshot = {}) {
  return requestClient.post('/system/users/delete', { id, ...snapshot });
}

export function resetSystemUserPasswordApi(
  id: number,
  password: string,
  snapshot: SystemAuditTargetSnapshot = {},
) {
  return requestClient.post('/system/users/reset_password', { id, password, ...snapshot });
}

export function batchUpdateSystemUserRolesApi(data: {
  mode: 'append' | 'replace';
  role_ids: number[];
  target_id?: string;
  target_label?: string;
  user_ids: number[];
}) {
  return requestClient.post('/system/users/batch_roles', data);
}

export function getSystemUserPermissionOverridesApi(id: number) {
  return requestClient.get<SystemUserPermissionOverrides>(
    `/system/users/${id}/permission_overrides`,
  );
}

export function saveSystemUserPermissionOverridesApi(
  id: number,
  data: { allow_codes: string[]; deny_codes: string[]; reason?: string; target_label?: string },
) {
  return requestClient.post(`/system/users/${id}/permission_overrides`, data);
}

export function getSystemRolesApi() {
  return requestClient.get<{ items: SystemRole[] }>('/system/roles');
}

export function saveSystemRoleApi(data: SystemRole) {
  return requestClient.post('/system/roles/save', data);
}

export function deleteSystemRoleApi(id: number, snapshot: SystemAuditTargetSnapshot = {}) {
  return requestClient.post('/system/roles/delete', { id, ...snapshot });
}

export function getSystemPermissionsApi() {
  return requestClient.get<{ items: SystemPermission[] }>('/system/permissions');
}

export function getSystemPermissionBundlesApi() {
  return requestClient.get<{ items: SystemPermissionBundle[] }>(
    '/system/permission_bundles',
  );
}

export function saveSystemPermissionBundleApi(data: SystemPermissionBundle) {
  return requestClient.post('/system/permission_bundles/save', data);
}

export function deleteSystemPermissionBundleApi(
  id: number,
  snapshot: SystemAuditTargetSnapshot = {},
) {
  return requestClient.post('/system/permission_bundles/delete', { id, ...snapshot });
}

export function getSystemOperationLogsApi(params: number | SystemOperationLogQuery = 100) {
  const query = typeof params === 'number' ? { limit: params } : params;
  return requestClient.get<{ items: SystemOperationLog[]; page?: number; page_size?: number; total?: number }>(
    '/system/operation_logs',
    {
      params: query,
    },
  );
}

export function getSystemOperationLogsByQueryApi(params: SystemOperationLogQuery) {
  return requestClient.get<{ items: SystemOperationLog[]; page: number; page_size: number; total: number }>(
    '/system/operation_logs',
    {
      params,
    },
  );
}
