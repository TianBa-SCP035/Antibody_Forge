<script setup lang="ts">
import type {
  SystemOperationLog,
  SystemOperationLogQuery,
  SystemPermission,
  SystemPermissionBundle,
  SystemRole,
  SystemUser,
  SystemUserPermissionOverrides,
} from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { useAccessStore, useUserStore } from '@vben/stores';

import {
  ElAlert,
  ElAutocomplete,
  ElButton,
  ElCard,
  ElCheckbox,
  ElCheckboxGroup,
  ElCol,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElRow,
  ElSelect,
  ElSpace,
  ElSwitch,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  batchUpdateSystemUserRolesApi,
  deleteSystemPermissionBundleApi,
  deleteSystemRoleApi,
  deleteSystemUserApi,
  getSystemOperationLogsByQueryApi,
  getSystemPermissionBundlesApi,
  getSystemPermissionsApi,
  getSystemRolesApi,
  getSystemUserPermissionOverridesApi,
  getSystemUserSuggestionsApi,
  getSystemUsersApi,
  resetSystemUserPasswordApi,
  saveSystemPermissionBundleApi,
  saveSystemRoleApi,
  saveSystemUserApi,
  saveSystemUserPermissionOverridesApi,
} from '#/api';
import { notifyApiError, resolveUserMessage } from '#/api/errors';
import { skipGlobalErrorHandler } from '#/api/request';
import { useStaleTabRefresh } from '#/utils/staleTabRefresh';
import { SYSTEM_ERRORS } from './errors';

defineOptions({ name: 'SystemUserPermission' });

const accessStore = useAccessStore();
const userStore = useUserStore();

const activeTab = ref('users');
const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');
const userKeyword = ref('');
const userDialogVisible = ref(false);
const passwordDialogVisible = ref(false);
const roleDialogVisible = ref(false);
const bundleDialogVisible = ref(false);
const batchRoleDialogVisible = ref(false);
const overrideDialogVisible = ref(false);
const overrideLoading = ref(false);
const selectedOverrideUser = ref<SystemUser | null>(null);
const selectedPasswordUser = ref<SystemUser | null>(null);
const userOverrideData = ref<SystemUserPermissionOverrides | null>(null);

const logQuery = reactive<SystemOperationLogQuery>({
  keyword: '',
  page: 1,
  page_size: 50,
  result: '',
  username: '',
});
const userQuery = reactive({
  page: 1,
  page_size: 50,
});
const logTotal = ref(0);
const userTotal = ref(0);
const activeUserTotal = ref(0);

const users = ref<SystemUser[]>([]);
const roles = ref<SystemRole[]>([]);
const permissions = ref<SystemPermission[]>([]);
const permissionBundles = ref<SystemPermissionBundle[]>([]);
const logs = ref<SystemOperationLog[]>([]);
const selectedUserRows = ref<SystemUser[]>([]);

const userFilters = reactive({
  department: '',
  employment_status: '',
  gender: '',
  group_name: '',
  status: '',
});

/** 客户端筛选：任一已绑定角色的名称包含「管理员」 */
const systemAdminRoleFilter = ref<'' | 'no' | 'yes'>('');

const userForm = reactive<SystemUser & { password?: string }>({
  username: '',
  display_name: '',
  openid: '',
  job_no: '',
  department: '',
  group_name: '',
  position_title: '',
  gender: '',
  profile_signature: '',
  employment_status: 'active',
  email: '',
  mobile: '',
  status: 'active',
  is_superuser: false,
  role_ids: [],
});

const roleForm = reactive<SystemRole>({
  code: '',
  name: '',
  description: '',
  status: 'active',
  sort_order: 0,
  bundle_codes: [],
});

const bundleForm = reactive<SystemPermissionBundle>({
  code: '',
  name: '',
  module: 'serum',
  description: '',
  status: 'active',
  sort_order: 0,
  permission_codes: [],
});

const overrideForm = reactive({
  allow_codes: [] as string[],
  deny_codes: [] as string[],
  reason: '',
});

const batchRoleForm = reactive({
  mode: 'replace' as 'append' | 'replace',
  role_ids: [] as number[],
});

const userPasswordForm = reactive({
  new_password: '',
});

const rolesWithId = computed(() => {
  return roles.value.filter((role) => typeof role.id === 'number') as Array<
    SystemRole & { id: number }
  >;
});

const roleNameMap = computed(() => {
  return new Map(rolesWithId.value.map((role) => [role.id, role.name]));
});

const permissionBundleMap = computed(() => {
  return new Map(permissionBundles.value.map((bundle) => [bundle.code, bundle]));
});

const permissionMap = computed(() => {
  return new Map(permissions.value.map((permission) => [permission.code, permission]));
});

const currentAccessCodes = computed(() => {
  const userInfo = userStore.userInfo as any;
  return new Set<string>([
    ...accessStore.accessCodes,
    ...((userInfo?.accessCodes as string[] | undefined) || []),
    ...((userInfo?.permissions as string[] | undefined) || []),
  ]);
});

const isCurrentSuperuser = computed(() => {
  return Boolean((userStore.userInfo as any)?.isSuperuser);
});

const canManageUsers = computed(() => hasSystemAccess('system.user.manage'));
const canManageRoles = computed(() => hasSystemAccess('system.role.manage'));
const canManagePermissions = computed(() => hasSystemAccess('system.permission.manage'));
const canViewLogs = computed(() => hasSystemAccess('system.operation_log.view'));
const canManageSuperuser = computed(() => isCurrentSuperuser.value);

const visibleTabs = computed(() => [
  ...(canManageUsers.value ? ['users'] : []),
  ...(canManageRoles.value ? ['roles'] : []),
  ...(canManagePermissions.value ? ['bundles', 'permissions'] : []),
  ...(canViewLogs.value ? ['logs'] : []),
]);

const activeUsersCount = computed(() => {
  return activeUserTotal.value;
});

const activeRolesCount = computed(() => {
  return roles.value.filter((role) => role.status === 'active').length;
});

const activePermissionBundlesCount = computed(() => {
  return permissionBundles.value.filter((bundle) => bundle.status === 'active').length;
});

const usersForTable = computed(() => {
  return users.value.map((user) => {
    const isSystemAdminRole = userRoleNameHasAdmin(user.role_ids);
    return {
      ...user,
      employment_status_text: formatEmploymentStatus(user.employment_status),
      gender_text: formatGender(user.gender),
      org_summary: [user.department, user.group_name].filter(Boolean).join(' / ') || '-',
      role_names: formatRoleNames(user.role_ids) || '-',
      is_system_admin_role: isSystemAdminRole,
      system_admin_text: isSystemAdminRole ? '是' : '否',
    };
  });
});

const rolesForTable = computed(() => {
  return roles.value.map((role) => ({
    ...role,
    bundle_names: formatBundleNames(role.bundle_codes),
    permission_count: getEffectiveRolePermissionCodes(role).length,
  }));
});

const bundlesForTable = computed(() => {
  return permissionBundles.value.map((bundle) => ({
    ...bundle,
    module_name: getPermissionModuleName(bundle.module),
    permission_count: bundle.permission_codes.length,
    status_text: bundle.status === 'active' ? '启用' : '禁用',
  }));
});

const permissionsForTable = computed(() => {
  return permissions.value.map((permission) => ({
    ...permission,
    module_name: getPermissionModuleName(permission.module || permission.code),
    type_name: getPermissionTypeName(permission.type),
    resource_name: permission.resource || '-',
    action_name: permission.action || '-',
    owner_page_name: getPermissionOwnerPageName(permission),
    route_path_text: permission.route_path || '-',
    ui_key_text: permission.ui_key || '-',
  }));
});

const groupedPermissions = computed(() => {
  const groups = new Map<string, typeof permissionsForTable.value>();
  for (const permission of permissionsForTable.value) {
    const groupKey = permission.owner_page_name;
    const list = groups.get(groupKey) || [];
    list.push(permission);
    groups.set(groupKey, list);
  }
  return [...groups.entries()].map(([name, items]) => ({ name, items }));
});

const groupedPermissionBundles = computed(() => {
  const groups = new Map<string, SystemPermissionBundle[]>();
  for (const bundle of permissionBundles.value) {
    const list = groups.get(bundle.module) || [];
    list.push(bundle);
    groups.set(bundle.module, list);
  }
  return [...groups.entries()].map(([name, items]) => ({
    name: getPermissionModuleName(name),
    items,
  }));
});

const overridePermissionRows = computed(() => {
  const rolePermissions = new Set(userOverrideData.value?.role_permissions || []);
  const allowCodes = new Set(overrideForm.allow_codes);
  const denyCodes = new Set(overrideForm.deny_codes);
  const effectivePermissions = new Set([...rolePermissions, ...allowCodes]);
  for (const code of denyCodes) {
    effectivePermissions.delete(code);
  }
  return permissionsForTable.value.map((permission) => ({
    ...permission,
    from_role: rolePermissions.has(permission.code),
    is_allowed: allowCodes.has(permission.code),
    is_denied: denyCodes.has(permission.code),
    is_effective: effectivePermissions.has(permission.code),
  }));
});

const groupedOverridePermissions = computed(() => {
  const groups = new Map<string, typeof overridePermissionRows.value>();
  for (const permission of overridePermissionRows.value) {
    const list = groups.get(permission.owner_page_name) || [];
    list.push(permission);
    groups.set(permission.owner_page_name, list);
  }
  return [...groups.entries()].map(([name, items]) => ({ name, items }));
});

function formatRoleNames(roleIds?: number[]) {
  return (roleIds || [])
    .map((roleId) => roleNameMap.value.get(roleId))
    .filter(Boolean)
    .join('、');
}

/** 角色名称含「管理员」即视为系统管理类角色，用于列表展示与筛选（不参与权限计算） */
function userRoleNameHasAdmin(roleIds?: number[]) {
  for (const roleId of roleIds || []) {
    const name = roleNameMap.value.get(roleId);
    if (name && name.includes('管理员')) {
      return true;
    }
  }
  return false;
}

function formatBundleNames(bundleCodes?: string[]) {
  const groups = new Map<string, string[]>();
  for (const code of bundleCodes || []) {
    const bundle = permissionBundleMap.value.get(code);
    const moduleName = bundle ? getPermissionModuleName(bundle.module) : '其他';
    const names = groups.get(moduleName) || [];
    names.push(bundle?.name || code);
    groups.set(moduleName, names);
  }
  return [...groups.entries()]
    .map(([moduleName, names]) => `${moduleName}：${names.join('、')}`)
    .join('；') || '-';
}

function getEffectiveRolePermissionCodes(role: SystemRole) {
  const result = new Set<string>();
  for (const bundleCode of role.bundle_codes || []) {
    const bundle = permissionBundleMap.value.get(bundleCode);
    if (!bundle || bundle.status !== 'active') continue;
    for (const permissionCode of bundle?.permission_codes || []) {
      const permission = permissionMap.value.get(permissionCode);
      if (permission?.status === 'active') {
        result.add(permissionCode);
      }
    }
  }
  return [...result];
}

function hasSystemAccess(code: string) {
  return (
    isCurrentSuperuser.value ||
    currentAccessCodes.value.has('*') ||
    currentAccessCodes.value.has(code)
  );
}

function ensureActiveTab() {
  if (!visibleTabs.value.includes(activeTab.value)) {
    activeTab.value = visibleTabs.value[0] || '';
  }
}

function getPermissionModuleName(value: string) {
  const moduleCode = value.includes('.') ? value.split('.')[0] || '' : value;
  const map: Record<string, string> = {
    serum: '小鼠免疫',
    mega: '镁伽自动化',
    system: '系统管理',
  };
  return map[moduleCode] || moduleCode || '其他';
}

function getPermissionTypeName(type: string) {
  const map: Record<string, string> = {
    action: '操作权限',
    button: '按钮/操作',
    data: '数据范围',
    module: '业务模块',
    page: '页面/路由',
  };
  return map[type] || type;
}

function getPermissionOwnerPageName(permission: SystemPermission) {
  if (permission.type === 'page') {
    return permission.name;
  }
  if (permission.parent_code) {
    const parent = permissions.value.find((item) => item.code === permission.parent_code);
    if (parent) return parent.name;
  }
  const resource = permission.resource ? ` / ${permission.resource}` : '';
  return `${getPermissionModuleName(permission.module || permission.code)}${resource}`;
}

function formatGender(gender?: string) {
  const map: Record<string, string> = {
    female: '女',
    male: '男',
    unknown: '未知',
  };
  return gender ? map[gender] || gender : '-';
}

function formatEmploymentStatus(status?: string) {
  const map: Record<string, string> = {
    active: '在职',
    on_leave: '休假中',
    resigned: '已离职',
  };
  return status ? map[status] || status : '-';
}

function getLogDetail(log: SystemOperationLog) {
  return log?.detail && typeof log.detail === 'object' ? log.detail : {};
}

function formatLogOperator(log: SystemOperationLog) {
  const detail = getLogDetail(log);
  const name = log.operator_name || detail.operator_name;
  if (name && log.username && name !== log.username) {
    return `${name}（${log.username}）`;
  }
  return name || log.username || '-';
}

function formatLogAction(log: SystemOperationLog) {
  const detail = getLogDetail(log);
  return log.operation_name || detail.operation_name || detail.permission_name || log.action || '-';
}

function formatLogTarget(log: SystemOperationLog) {
  const detail = getLogDetail(log);
  const label = log.target_label || detail.target_label;
  const type = formatLogTargetType(log);
  if (label && log.target_id && String(label) !== String(log.target_id)) {
    return `${type}：${label} / ID ${log.target_id}`;
  }
  if (label) return `${type}：${label}`;
  if (log.target_id) return `${type}：ID ${log.target_id}`;
  return '-';
}

function formatLogTargetType(log: SystemOperationLog) {
  const map: Record<string, string> = {
    bundle: '权限包',
    cage: '笼位',
    cell: '细胞库存',
    feature: '系统功能',
    file: '文件',
    flow_work_order: '工单',
    mouse: '小鼠数据',
    operation_log: '操作日志',
    permission: '权限',
    project: '免疫项目',
    project_status: '项目状态',
    role: '角色',
    sys_user: '用户',
    titer: '效价',
    titer_order: '效价工单',
    user: '用户',
  };
  return log.target_type ? map[log.target_type] || log.target_type : '-';
}

function formatLogResult(result?: string) {
  const map: Record<string, string> = {
    failed: '失败',
    success: '成功',
  };
  return result ? map[result] || result : '-';
}

function resetRolePermissions() {
  roleForm.bundle_codes = [];
}

function resetBundleForm(bundle?: SystemPermissionBundle) {
  Object.assign(bundleForm, {
    id: bundle?.id,
    code: bundle?.code || '',
    name: bundle?.name || '',
    module: bundle?.module || 'serum',
    description: bundle?.description || '',
    status: bundle?.status || 'active',
    sort_order: bundle?.sort_order || 0,
    permission_codes: bundle?.permission_codes || [],
  });
}

function resetUserForm(user?: SystemUser) {
  Object.assign(userForm, {
    id: user?.id,
    username: user?.username || '',
    display_name: user?.display_name || '',
    openid: user?.openid || '',
    job_no: user?.job_no || '',
    department: user?.department || '',
    group_name: user?.group_name || '',
    position_title: user?.position_title || '',
    gender: user?.gender || '',
    profile_signature: user?.profile_signature || '',
    employment_status: user?.employment_status || 'active',
    email: user?.email || '',
    mobile: user?.mobile || '',
    status: user?.status || 'active',
    is_superuser: Boolean(user?.is_superuser),
    role_ids: user?.role_ids || [],
    password: '',
  });
  userPasswordForm.new_password = '';
}

function resetRoleForm(role?: SystemRole) {
  Object.assign(roleForm, {
    id: role?.id,
    code: role?.code || '',
    name: role?.name || '',
    description: role?.description || '',
    status: role?.status || 'active',
    sort_order: role?.sort_order || 0,
    bundle_codes: role?.bundle_codes || [],
  });
}

function openBundleDialog(bundle?: SystemPermissionBundle) {
  resetBundleForm(bundle);
  bundleDialogVisible.value = true;
}

async function loadData() {
  loading.value = true;
  errorMessage.value = '';
  try {
    ensureActiveTab();
    if (canManageUsers.value) {
      const userResult = await getSystemUsersApi({
        ...userFilters,
        has_admin_role: systemAdminRoleFilter.value,
        keyword: userKeyword.value.trim(),
        page: userQuery.page,
        page_size: userQuery.page_size,
      }, skipGlobalErrorHandler);
      users.value = userResult?.items || [];
      userTotal.value = userResult?.total || users.value.length;
      activeUserTotal.value = userResult?.active_total || 0;
    } else {
      users.value = [];
      userTotal.value = 0;
      activeUserTotal.value = 0;
      selectedUserRows.value = [];
    }

    if (canManageRoles.value) {
      const roleResult = await getSystemRolesApi(skipGlobalErrorHandler);
      roles.value = roleResult?.items || [];
    } else {
      roles.value = [];
    }

    if (canManagePermissions.value) {
      const [permissionResult, bundleResult] = await Promise.all([
        getSystemPermissionsApi(skipGlobalErrorHandler),
        getSystemPermissionBundlesApi(skipGlobalErrorHandler),
      ]);
      permissions.value = permissionResult?.items || [];
      permissionBundles.value = bundleResult?.items || [];
    } else {
      permissions.value = [];
      permissionBundles.value = [];
    }

    if (canViewLogs.value) {
      const logResult = await getSystemOperationLogsByQueryApi(logQuery, skipGlobalErrorHandler);
      logs.value = logResult?.items || [];
      logTotal.value = logResult?.total || logs.value.length;
    } else {
      logs.value = [];
      logTotal.value = 0;
    }

    if (!visibleTabs.value.length) {
      errorMessage.value = '当前账号没有用户权限管理明细权限';
    }
  } catch (error: unknown) {
    errorMessage.value = resolveUserMessage(error, {
      messages: SYSTEM_ERRORS.loadData,
    }).message;
  } finally {
    loading.value = false;
    markTabDataFetched();
  }
}

const { markTabDataFetched } = useStaleTabRefresh(loadData);

async function loadLogs() {
  if (!canViewLogs.value) return;
  loading.value = true;
  try {
    const result = await getSystemOperationLogsByQueryApi(logQuery);
    logs.value = result?.items || [];
    logTotal.value = result?.total || logs.value.length;
  } finally {
    loading.value = false;
  }
}

function handleUserSearch() {
  userQuery.page = 1;
  selectedUserRows.value = [];
  loadData();
}

function handleUserPageChange(page: number) {
  userQuery.page = page;
  selectedUserRows.value = [];
  loadData();
}

async function fetchUserSuggestions(
  field: 'department' | 'group_name' | 'keyword',
  query: string,
  callback: (items: Array<{ value: string }>) => void,
) {
  try {
    const result = await getSystemUserSuggestionsApi({
      field,
      keyword: query,
      limit: 20,
    });
    callback((result?.items || []).map((value) => ({ value })));
  } catch {
    callback([]);
  }
}

function fetchKeywordSuggestions(query: string, callback: (items: Array<{ value: string }>) => void) {
  fetchUserSuggestions('keyword', query, callback);
}

function fetchDepartmentSuggestions(query: string, callback: (items: Array<{ value: string }>) => void) {
  fetchUserSuggestions('department', query, callback);
}

function fetchGroupSuggestions(query: string, callback: (items: Array<{ value: string }>) => void) {
  fetchUserSuggestions('group_name', query, callback);
}

function handleUserSuggestionSelect() {
  handleUserSearch();
}

function openUserDialog(user?: SystemUser) {
  resetUserForm(user);
  userDialogVisible.value = true;
}

function openPasswordDialog(user: SystemUser) {
  if (!user.id) return;
  selectedPasswordUser.value = user;
  userPasswordForm.new_password = '';
  passwordDialogVisible.value = true;
}

function handleUserSelectionChange(rows: SystemUser[]) {
  selectedUserRows.value = rows;
}

function openBatchRoleDialog() {
  if (!selectedUserRows.value.length) {
    ElMessage.warning('请先勾选用户');
    return;
  }
  batchRoleForm.mode = 'replace';
  batchRoleForm.role_ids = [];
  batchRoleDialogVisible.value = true;
}

async function saveBatchRoles() {
  const userIds = selectedUserRows.value
    .map((user) => user.id)
    .filter((id): id is number => typeof id === 'number');
  if (!userIds.length) {
    ElMessage.warning('请先勾选用户');
    return;
  }
  if (!batchRoleForm.role_ids.length) {
    ElMessage.warning('请选择角色');
    return;
  }

  saving.value = true;
  try {
    await batchUpdateSystemUserRolesApi({
      mode: batchRoleForm.mode,
      role_ids: batchRoleForm.role_ids,
      target_id: userIds.join(','),
      target_label: `共 ${userIds.length} 个用户`,
      user_ids: userIds,
    });
    ElMessage.success('角色已批量更新');
    batchRoleDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function saveUser() {
  if (!userForm.username.trim()) {
    ElMessage.warning('请输入用户名');
    return;
  }
  if (!userForm.id && (!userForm.password || userForm.password.length < 6)) {
    ElMessage.warning('新增用户需要设置至少 6 位登录密码');
    return;
  }

  saving.value = true;
  try {
    await saveSystemUserApi(userForm);
    ElMessage.success('用户已保存');
    userDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function deleteUser() {
  if (!userForm.id) return;
  const confirmed = await ElMessageBox.confirm(
    `确认删除账号 ${userForm.username} 吗？相关角色关系和个人权限覆盖会一并清理。`,
    '删除账号',
    {
      cancelButtonText: '取消',
      confirmButtonText: '删除',
      type: 'warning',
    },
  ).catch(() => false);
  if (!confirmed) return;

  saving.value = true;
  try {
    await deleteSystemUserApi(userForm.id, {
      display_name: userForm.display_name,
      target_label: userForm.display_name || userForm.username,
      username: userForm.username,
    });
    ElMessage.success('账号已删除');
    userDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

function generateTemporaryPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@#$%';
  const values = new Uint32Array(12);
  crypto.getRandomValues(values);
  return [...values].map((value) => chars[value % chars.length]).join('');
}

function fillInitialPassword() {
  userForm.password = generateTemporaryPassword();
}

function fillResetPassword() {
  userPasswordForm.new_password = generateTemporaryPassword();
}

async function resetCurrentUserPassword() {
  if (!selectedPasswordUser.value?.id) return;
  if (userPasswordForm.new_password.length < 6) {
    ElMessage.warning('请输入至少 6 位新密码');
    return;
  }
  saving.value = true;
  try {
    await resetSystemUserPasswordApi(
      selectedPasswordUser.value.id,
      userPasswordForm.new_password,
      {
        target_label:
          selectedPasswordUser.value.display_name || selectedPasswordUser.value.username,
        username: selectedPasswordUser.value.username,
      },
    );
    userPasswordForm.new_password = '';
    passwordDialogVisible.value = false;
    ElMessage.success('密码已重置');
  } finally {
    saving.value = false;
  }
}

async function openOverrideDialog(user: SystemUser) {
  if (!user.id) return;
  selectedOverrideUser.value = user;
  userOverrideData.value = null;
  overrideForm.allow_codes = [];
  overrideForm.deny_codes = [];
  overrideForm.reason = '';
  overrideDialogVisible.value = true;
  overrideLoading.value = true;
  try {
    const result = await getSystemUserPermissionOverridesApi(user.id, skipGlobalErrorHandler);
    userOverrideData.value = result;
    overrideForm.allow_codes = result.overrides
      .filter((item) => item.effect === 'allow')
      .map((item) => item.permission_code);
    overrideForm.deny_codes = result.overrides
      .filter((item) => item.effect === 'deny')
      .map((item) => item.permission_code);
    overrideForm.reason = result.overrides[0]?.reason || '';
  } catch (error: unknown) {
    userOverrideData.value = null;
    overrideForm.allow_codes = [];
    overrideForm.deny_codes = [];
    overrideForm.reason = '';
    notifyApiError(error, { messages: SYSTEM_ERRORS.loadOverride });
  } finally {
    overrideLoading.value = false;
  }
}

function toggleOverridePermission(code: string, effect: 'allow' | 'deny', checked: boolean) {
  const target = effect === 'allow' ? overrideForm.allow_codes : overrideForm.deny_codes;
  const other = effect === 'allow' ? overrideForm.deny_codes : overrideForm.allow_codes;
  if (checked && !target.includes(code)) {
    target.push(code);
  }
  if (!checked) {
    const index = target.indexOf(code);
    if (index >= 0) target.splice(index, 1);
  }
  if (checked) {
    const otherIndex = other.indexOf(code);
    if (otherIndex >= 0) other.splice(otherIndex, 1);
  }
}

async function saveUserOverrides() {
  if (!selectedOverrideUser.value?.id) return;
  saving.value = true;
  try {
    await saveSystemUserPermissionOverridesApi(selectedOverrideUser.value.id, {
      allow_codes: overrideForm.allow_codes,
      deny_codes: overrideForm.deny_codes,
      reason: overrideForm.reason,
      target_label:
        selectedOverrideUser.value.display_name || selectedOverrideUser.value.username,
    });
    ElMessage.success('个人权限已保存');
    overrideDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

function openRoleDialog(role?: SystemRole) {
  resetRoleForm(role);
  roleDialogVisible.value = true;
}

async function saveRole() {
  if (!roleForm.code.trim() || !roleForm.name.trim()) {
    ElMessage.warning('请输入角色编码和角色名称');
    return;
  }

  saving.value = true;
  try {
    await saveSystemRoleApi(roleForm);
    ElMessage.success('角色已保存');
    roleDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function deleteRole() {
  if (!roleForm.id) return;
  const confirmed = await ElMessageBox.confirm(
    `确认删除角色 ${roleForm.name || roleForm.code} 吗？用户角色关系会一并清理。`,
    '删除角色',
    {
      cancelButtonText: '取消',
      confirmButtonText: '删除',
      type: 'warning',
    },
  ).catch(() => false);
  if (!confirmed) return;

  saving.value = true;
  try {
    await deleteSystemRoleApi(roleForm.id, {
      code: roleForm.code,
      name: roleForm.name,
      target_label: roleForm.name || roleForm.code,
    });
    ElMessage.success('角色已删除');
    roleDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function saveBundle() {
  if (!bundleForm.code.trim() || !bundleForm.name.trim()) {
    ElMessage.warning('请输入权限包编码和名称');
    return;
  }

  saving.value = true;
  try {
    await saveSystemPermissionBundleApi(bundleForm);
    ElMessage.success('权限包已保存');
    bundleDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function deleteBundle() {
  if (!bundleForm.id) return;
  const confirmed = await ElMessageBox.confirm(
    `确认删除权限包 ${bundleForm.name || bundleForm.code} 吗？角色引用和包内权限点关系会一并清理。`,
    '删除权限包',
    {
      cancelButtonText: '取消',
      confirmButtonText: '删除',
      type: 'warning',
    },
  ).catch(() => false);
  if (!confirmed) return;

  saving.value = true;
  try {
    await deleteSystemPermissionBundleApi(bundleForm.id, {
      code: bundleForm.code,
      name: bundleForm.name,
      target_label: bundleForm.name || bundleForm.code,
    });
    ElMessage.success('权限包已删除');
    bundleDialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

function statusTagType(status?: string) {
  return status === 'active' ? 'success' : 'info';
}

function handleLogPageChange(page: number) {
  logQuery.page = page;
  void loadLogs();
}

onMounted(loadData);
</script>

<template>
  <div class="system-page">
    <div class="system-header">
      <div>
        <h2>用户权限</h2>
        <p>账号、角色权限、个人权限覆盖与操作审计</p>
      </div>
      <el-button :loading="loading" type="primary" @click="loadData">
        刷新数据
      </el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      class="section-gap"
      :title="errorMessage"
      show-icon
      type="error"
    />

    <el-row :gutter="12" class="summary-row">
      <el-col :lg="6" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <span>用户</span>
          <strong>{{ activeUsersCount }} / {{ userTotal }}</strong>
        </el-card>
      </el-col>
      <el-col :lg="6" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <span>角色</span>
          <strong>{{ activeRolesCount }} / {{ roles.length }}</strong>
        </el-card>
      </el-col>
      <el-col :lg="6" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <span>权限包</span>
          <strong>{{ activePermissionBundlesCount }} / {{ permissionBundles.length }}</strong>
        </el-card>
      </el-col>
      <el-col :lg="6" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <span>权限点</span>
          <strong>{{ permissions.length }}</strong>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane v-if="canManageUsers" label="用户管理" name="users">
          <div class="table-toolbar">
            <el-space wrap>
              <el-autocomplete
                v-model="userKeyword"
                clearable
                :debounce="250"
                :fetch-suggestions="fetchKeywordSuggestions"
                placeholder="搜索账号、姓名、工号"
                style="width: 220px"
                value-key="value"
                @clear="handleUserSearch"
                @keyup.enter="handleUserSearch"
                @select="handleUserSuggestionSelect"
              />
              <el-autocomplete
                v-model="userFilters.department"
                clearable
                :debounce="250"
                :fetch-suggestions="fetchDepartmentSuggestions"
                placeholder="部门"
                style="width: 140px"
                value-key="value"
                @clear="handleUserSearch"
                @keyup.enter="handleUserSearch"
                @select="handleUserSuggestionSelect"
              />
              <el-autocomplete
                v-model="userFilters.group_name"
                clearable
                :debounce="250"
                :fetch-suggestions="fetchGroupSuggestions"
                placeholder="组别"
                style="width: 140px"
                value-key="value"
                @clear="handleUserSearch"
                @keyup.enter="handleUserSearch"
                @select="handleUserSuggestionSelect"
              />
              <el-select
                v-model="userFilters.gender"
                clearable
                placeholder="性别"
                style="width: 110px"
                @change="handleUserSearch"
              >
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
                <el-option label="未知" value="unknown" />
              </el-select>
              <el-select
                v-model="userFilters.status"
                clearable
                placeholder="账号状态"
                style="width: 120px"
                @change="handleUserSearch"
              >
                <el-option label="启用" value="active" />
                <el-option label="禁用" value="disabled" />
              </el-select>
              <el-select
                v-model="userFilters.employment_status"
                clearable
                placeholder="在职状态"
                style="width: 120px"
                @change="handleUserSearch"
              >
                <el-option label="在职" value="active" />
                <el-option label="休假中" value="on_leave" />
                <el-option label="已离职" value="resigned" />
              </el-select>
              <el-select
                v-model="systemAdminRoleFilter"
                clearable
                placeholder="系统管理员"
                style="width: 130px"
                @change="handleUserSearch"
              >
                <el-option label="是" value="yes" />
                <el-option label="否" value="no" />
              </el-select>
              <el-button :loading="loading" @click="handleUserSearch">查询</el-button>
            </el-space>
            <el-space>
              <el-button @click="openBatchRoleDialog">
                批量设置角色
              </el-button>
              <el-button type="primary" @click="openUserDialog()">
                新增用户
              </el-button>
            </el-space>
          </div>

          <el-table
            v-loading="loading"
            :data="usersForTable"
            border
            stripe
            @selection-change="handleUserSelectionChange"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column prop="username" label="账号" min-width="130" />
            <el-table-column prop="display_name" label="姓名" min-width="140" />
            <el-table-column prop="org_summary" label="部门/组别" min-width="160" />
            <el-table-column prop="role_names" label="角色" min-width="180" />
            <el-table-column prop="employment_status_text" label="在职状态" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)">
                  {{ row.status === 'active' ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="系统管理员" width="120">
              <template #default="{ row }">
                <el-tag :type="row.is_system_admin_role ? 'danger' : 'info'">
                  {{ row.system_admin_text }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openUserDialog(row)">
                  编辑资料
                </el-button>
                <el-button
                  v-if="canManagePermissions"
                  link
                  type="success"
                  @click="openOverrideDialog(row)"
                >
                  个人权限
                </el-button>
                <el-button link type="warning" @click="openPasswordDialog(row)">
                  账号密码
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-line">
            <el-pagination
              background
              layout="prev, pager, next, total"
              :current-page="userQuery.page"
              :page-size="userQuery.page_size"
              :total="userTotal"
              @current-change="handleUserPageChange"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="canManageRoles" label="角色管理" name="roles">
          <div class="table-toolbar">
            <div class="hint-text">角色只分配权限包；个人例外权限在用户管理中单独设置。</div>
            <el-button type="primary" @click="openRoleDialog()">
              新增角色
            </el-button>
          </div>

          <el-table v-loading="loading" :data="rolesForTable" border stripe>
            <el-table-column prop="code" label="角色编码" min-width="160" />
            <el-table-column prop="name" label="角色名称" min-width="140" />
            <el-table-column prop="description" label="描述" min-width="220" />
            <el-table-column prop="bundle_names" label="匹配权限包" min-width="260" />
            <el-table-column prop="permission_count" label="权限数" width="90" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)">
                  {{ row.status === 'active' ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRoleDialog(row)">
                  编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane v-if="canManagePermissions" label="权限包" name="bundles">
          <div class="table-toolbar">
            <div class="hint-text">权限包负责把一组页面和操作权限打包，再分配给角色。</div>
            <el-button type="primary" @click="openBundleDialog()">
              新增权限包
            </el-button>
          </div>

          <el-table v-loading="loading" :data="bundlesForTable" border stripe>
            <el-table-column prop="code" label="权限包编码" min-width="180" />
            <el-table-column prop="module_name" label="业务模块" width="120" />
            <el-table-column prop="name" label="包名称" min-width="140" />
            <el-table-column prop="description" label="描述" min-width="260" />
            <el-table-column prop="permission_count" label="权限点" width="90" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)">
                  {{ row.status_text }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openBundleDialog(row)">
                  编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane v-if="canManagePermissions" label="权限点" name="permissions">
          <el-alert
            class="section-gap"
            show-icon
            title="权限点按页面或业务归属展示。权限码由代码和初始化 SQL 维护，页面暂时只读。"
            type="info"
          />
          <el-empty v-if="!groupedPermissions.length" description="暂无权限点" />
          <div
            v-for="group in groupedPermissions"
            v-else
            :key="group.name"
            class="permission-table-group"
          >
            <div class="permission-table-title">{{ group.name }}</div>
            <el-table v-loading="loading" :data="group.items" border stripe>
              <el-table-column prop="name" label="功能" min-width="150" />
              <el-table-column prop="type_name" label="类型" width="120" />
              <el-table-column prop="action_name" label="动作" width="120" />
              <el-table-column prop="code" label="权限码" min-width="220" />
              <el-table-column prop="route_path_text" label="路由" min-width="150" />
              <el-table-column prop="ui_key_text" label="UI 标识" min-width="180" />
              <el-table-column prop="status" label="状态" width="90" />
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="canViewLogs" label="操作日志" name="logs">
          <div class="table-toolbar">
            <el-space wrap>
              <el-input
                v-model="logQuery.keyword"
                clearable
                placeholder="搜索账号、权限动作、目标或结果"
                style="width: 240px"
              />
              <el-input
                v-model="logQuery.username"
                clearable
                placeholder="操作账号"
                style="width: 160px"
              />
              <el-select v-model="logQuery.result" clearable placeholder="结果" style="width: 120px">
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-button :loading="loading" @click="loadLogs">查询</el-button>
            </el-space>
          </div>

          <el-table v-loading="loading" :data="logs" border stripe>
            <el-table-column label="操作人" min-width="160">
              <template #default="{ row }">
                {{ formatLogOperator(row) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="190">
              <template #default="{ row }">
                {{ formatLogAction(row) }}
              </template>
            </el-table-column>
            <el-table-column label="目标类型" min-width="120">
              <template #default="{ row }">
                {{ formatLogTargetType(row) }}
              </template>
            </el-table-column>
            <el-table-column label="目标" min-width="160">
              <template #default="{ row }">
                {{ formatLogTarget(row) }}
              </template>
            </el-table-column>
            <el-table-column label="结果" width="100">
              <template #default="{ row }">
                {{ formatLogResult(row.result) }}
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="失败原因" min-width="220" />
            <el-table-column prop="created_at" label="时间" min-width="170" />
          </el-table>
          <div class="pagination-line">
            <el-pagination
              background
              layout="prev, pager, next, total"
              :current-page="logQuery.page"
              :page-size="logQuery.page_size"
              :total="logTotal"
              @current-change="handleLogPageChange"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="userDialogVisible" title="用户资料" width="820px">
      <el-form :model="userForm" label-width="110px">
        <div class="dialog-section">
          <div class="dialog-section-title">账号信息</div>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="账号">
                <el-input
                  v-model="userForm.username"
                  :disabled="Boolean(userForm.id)"
                  placeholder="登录账号"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="姓名">
                <el-input v-model="userForm.display_name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="工号">
                <el-input v-model="userForm.job_no" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="账号状态">
                <el-select v-model="userForm.status" style="width: 100%">
                  <el-option label="启用" value="active" />
                  <el-option label="禁用" value="disabled" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col v-if="!userForm.id" :span="24">
              <el-form-item label="初始密码">
                <el-input
                  v-model="userForm.password"
                  placeholder="新增用户必须设置初始密码"
                  show-password
                  type="password"
                >
                  <template #append>
                    <el-button @click="fillInitialPassword">生成临时密码</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">组织资料</div>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="部门">
                <el-input v-model="userForm.department" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="组别">
                <el-input v-model="userForm.group_name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="职位">
                <el-input v-model="userForm.position_title" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="在职状态">
                <el-select v-model="userForm.employment_status" style="width: 100%">
                  <el-option label="在职" value="active" />
                  <el-option label="休假中" value="on_leave" />
                  <el-option label="已离职" value="resigned" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="性别">
                <el-select v-model="userForm.gender" clearable style="width: 100%">
                  <el-option label="男" value="male" />
                  <el-option label="女" value="female" />
                  <el-option label="未知" value="unknown" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="手机号">
                <el-input v-model="userForm.mobile" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="邮箱">
                <el-input v-model="userForm.email" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="云之家 OpenID">
                <el-input v-model="userForm.openid" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="个性名片">
                <el-input
                  v-model="userForm.profile_signature"
                  maxlength="255"
                  show-word-limit
                  placeholder="例如：专注抗体工程与免疫效价数据"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">角色权限</div>
          <el-row :gutter="12">
            <el-col :span="18">
              <el-form-item label="角色">
                <el-select
                  v-model="userForm.role_ids"
                  multiple
                  placeholder="选择角色"
                  style="width: 100%"
                >
                  <el-option
                    v-for="role in rolesWithId"
                    :key="role.id"
                    :label="role.name"
                    :value="role.id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="超级管理员">
                <el-switch v-model="userForm.is_superuser" :disabled="!canManageSuperuser" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div v-if="userForm.id" class="dialog-section danger-section">
          <div class="dialog-section-title">危险操作</div>
          <div class="danger-line">
            <div>
              <p>删除后会清理角色关系和个人权限覆盖，操作会记录到日志。</p>
            </div>
            <el-button :loading="saving" type="danger" @click="deleteUser">
              删除账号
            </el-button>
          </div>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer-line">
          <span></span>
          <el-space>
            <el-button @click="userDialogVisible = false">取消</el-button>
            <el-button :loading="saving" type="primary" @click="saveUser">
              保存
            </el-button>
          </el-space>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="passwordDialogVisible"
      :title="`账号密码 - ${selectedPasswordUser?.display_name || selectedPasswordUser?.username || ''}`"
      width="560px"
    >
      <el-alert
        class="section-gap"
        show-icon
        title="系统不会展示原密码。这里只能设置新密码，生成的临时密码只在当前输入框中可见。"
        type="info"
      />
      <el-form label-width="90px">
        <el-form-item label="账号">
          <el-input :model-value="selectedPasswordUser?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="userPasswordForm.new_password"
            placeholder="输入新密码，至少 6 位"
            show-password
            type="password"
          >
            <template #append>
              <el-button @click="fillResetPassword">生成临时密码</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button
          :disabled="userPasswordForm.new_password.length < 6"
          :loading="saving"
          type="warning"
          @click="resetCurrentUserPassword"
        >
          重置密码
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchRoleDialogVisible" title="批量设置角色" width="560px">
      <el-alert
        class="section-gap"
        show-icon
        :title="`已选择 ${selectedUserRows.length} 个用户`"
        type="info"
      />
      <el-form :model="batchRoleForm" label-width="100px">
        <el-form-item label="处理方式">
          <el-select v-model="batchRoleForm.mode" style="width: 100%">
            <el-option label="覆盖原有角色" value="replace" />
            <el-option label="追加到原有角色" value="append" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="batchRoleForm.role_ids"
            multiple
            placeholder="选择角色"
            style="width: 100%"
          >
            <el-option
              v-for="role in rolesWithId"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRoleDialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="saveBatchRoles">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="roleDialogVisible" title="角色权限" width="920px">
      <el-form :model="roleForm" label-width="100px">
        <div class="dialog-section">
          <div class="dialog-section-title">角色信息</div>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="角色编码">
                <el-input v-model="roleForm.code" :disabled="Boolean(roleForm.id)" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="角色名称">
                <el-input v-model="roleForm.name" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="描述">
                <el-input v-model="roleForm.description" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="状态">
                <el-select v-model="roleForm.status" style="width: 100%">
                  <el-option label="启用" value="active" />
                  <el-option label="禁用" value="disabled" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="排序">
                <el-input-number v-model="roleForm.sort_order" :min="0" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">权限包</div>
          <el-form-item label="权限包">
            <div class="bundle-list">
              <el-empty v-if="!groupedPermissionBundles.length" description="暂无权限包" />
              <div
                v-for="group in groupedPermissionBundles"
                v-else
                :key="group.name"
                class="bundle-group"
              >
                <div class="bundle-group-title">{{ group.name }}</div>
                <el-checkbox-group v-model="roleForm.bundle_codes">
                  <el-checkbox
                    v-for="bundle in group.items"
                    :key="bundle.code"
                    :label="bundle.code"
                    class="bundle-card"
                  >
                    <div class="bundle-card-main">
                      <strong>{{ bundle.name }}</strong>
                      <p>{{ bundle.description }}</p>
                      <span>{{ bundle.permission_codes.length }} 个底层权限点</span>
                    </div>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <div class="bundle-actions">
                <el-button link type="danger" @click="resetRolePermissions">
                  清空已选权限包
                </el-button>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="最终权限">
            <div class="permission-preview">
              当前角色保存后将获得
              <strong>{{ getEffectiveRolePermissionCodes(roleForm).length }}</strong>
              个权限点。
            </div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer-line">
          <el-button v-if="roleForm.id" :loading="saving" type="danger" @click="deleteRole">
            删除角色
          </el-button>
          <el-space>
            <el-button @click="roleDialogVisible = false">取消</el-button>
            <el-button :loading="saving" type="primary" @click="saveRole">
              保存
            </el-button>
          </el-space>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="bundleDialogVisible" title="权限包" width="920px">
      <el-form :model="bundleForm" label-width="110px">
        <div class="dialog-section">
          <div class="dialog-section-title">权限包信息</div>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="权限包编码">
                <el-input v-model="bundleForm.code" :disabled="Boolean(bundleForm.id)" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="包名称">
                <el-input v-model="bundleForm.name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="业务模块">
                <el-select v-model="bundleForm.module" style="width: 100%">
                  <el-option label="小鼠免疫" value="serum" />
                  <el-option label="镁伽自动化" value="mega" />
                  <el-option label="系统管理" value="system" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="状态">
                <el-select v-model="bundleForm.status" style="width: 100%">
                  <el-option label="启用" value="active" />
                  <el-option label="禁用" value="disabled" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="排序">
                <el-input-number v-model="bundleForm.sort_order" :min="0" />
              </el-form-item>
            </el-col>
            <el-col :span="24">
              <el-form-item label="描述">
                <el-input v-model="bundleForm.description" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="dialog-section">
          <div class="dialog-section-title">包含权限点</div>
          <el-form-item label="权限点">
            <div class="permission-groups">
              <el-empty v-if="!groupedPermissions.length" description="暂无权限点" />
              <div
                v-for="group in groupedPermissions"
                v-else
                :key="group.name"
                class="permission-group"
              >
                <div class="permission-group-title">{{ group.name }}</div>
                <el-checkbox-group v-model="bundleForm.permission_codes">
                  <el-checkbox
                    v-for="permission in group.items"
                    :key="permission.code"
                    :label="permission.code"
                  >
                    {{ permission.name }}（{{ permission.type_name }}）
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer-line">
          <el-button v-if="bundleForm.id" :loading="saving" type="danger" @click="deleteBundle">
            删除权限包
          </el-button>
          <el-space>
            <el-button @click="bundleDialogVisible = false">取消</el-button>
            <el-button :loading="saving" type="primary" @click="saveBundle">
              保存
            </el-button>
          </el-space>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="overrideDialogVisible"
      :title="`个人权限覆盖 - ${selectedOverrideUser?.display_name || selectedOverrideUser?.username || ''}`"
      width="980px"
    >
      <el-alert
        class="section-gap"
        show-icon
        title="个人权限覆盖只用于例外情况：允许会额外增加权限，拒绝会覆盖角色权限。"
        type="warning"
      />
      <el-form label-width="90px">
        <el-form-item label="原因">
          <el-input
            v-model="overrideForm.reason"
            placeholder="填写调整原因，便于后续审计"
          />
        </el-form-item>
      </el-form>
      <div v-loading="overrideLoading" class="override-permission-groups">
        <el-empty v-if="!groupedOverridePermissions.length" description="暂无权限点" />
        <div
          v-for="group in groupedOverridePermissions"
          v-else
          :key="group.name"
          class="permission-table-group"
        >
          <div class="permission-table-title">{{ group.name }}</div>
          <el-table :data="group.items" border stripe>
            <el-table-column prop="name" label="权限" min-width="150" />
            <el-table-column prop="type_name" label="类型" width="110" />
            <el-table-column prop="code" label="权限码" min-width="220" />
            <el-table-column label="角色带来" width="90">
              <template #default="{ row }">
                <el-tag :type="row.from_role ? 'success' : 'info'">
                  {{ row.from_role ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="额外允许" width="100">
              <template #default="{ row }">
                <el-checkbox
                  :model-value="row.is_allowed"
                  @change="(checked) => toggleOverridePermission(row.code, 'allow', Boolean(checked))"
                />
              </template>
            </el-table-column>
            <el-table-column label="明确拒绝" width="100">
              <template #default="{ row }">
                <el-checkbox
                  :model-value="row.is_denied"
                  @change="(checked) => toggleOverridePermission(row.code, 'deny', Boolean(checked))"
                />
              </template>
            </el-table-column>
            <el-table-column label="最终有效" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_effective ? 'success' : 'info'">
                  {{ row.is_effective ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="overrideDialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="saveUserOverrides">
          保存个人权限
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.system-page {
  padding: 16px;
}

.system-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #e8eef7;
  border-radius: 12px;
}

.system-header h2 {
  margin: 0;
  color: #1f2937;
  font-size: 22px;
  font-weight: 700;
}

.system-header p {
  margin: 4px 0 0;
  color: #64748b;
}

.summary-row {
  margin-bottom: 12px;
}

.summary-card {
  margin-bottom: 12px;
  border-radius: 12px;
}

.summary-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
}

.summary-card span {
  color: #64748b;
}

.summary-card strong {
  color: #1f2937;
  font-size: 24px;
}

.main-card {
  border-radius: 12px;
}

.section-gap {
  margin-bottom: 12px;
}

.dialog-section {
  padding: 14px 14px 2px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
}

.dialog-section-title {
  margin-bottom: 12px;
  color: #334155;
  font-weight: 700;
}

.inline-actions {
  display: flex;
  justify-content: flex-end;
  margin: -2px 0 10px;
}

.danger-section {
  background: #fff7f7;
  border-color: #ffd6d6;
}

.danger-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
}

.danger-line strong {
  color: #991b1b;
}

.danger-line p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.hint-text {
  color: #64748b;
  font-size: 13px;
}

.bundle-list {
  width: 100%;
}

.bundle-group {
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
}

.bundle-group-title {
  margin-bottom: 10px;
  color: #334155;
  font-weight: 700;
}

.bundle-card {
  width: calc(50% - 8px);
  height: auto;
  padding: 10px 12px;
  margin: 0 8px 10px 0;
  vertical-align: top;
  background: #fff;
  border: 1px solid #e5eaf3;
  border-radius: 10px;
}

.bundle-card :deep(.el-checkbox__label) {
  width: 100%;
  white-space: normal;
}

.bundle-card-main p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.bundle-card-main span {
  display: inline-block;
  margin-top: 6px;
  color: #2563eb;
  font-size: 12px;
}

.bundle-actions {
  margin-top: 4px;
}

.permission-hint {
  margin-bottom: 10px;
}

.permission-preview {
  padding: 10px 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
}

.permission-table-group {
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
}

.permission-table-title {
  margin-bottom: 10px;
  color: #334155;
  font-weight: 700;
}

.override-permission-groups {
  max-height: 520px;
  padding-right: 6px;
  overflow: auto;
}

.permission-groups {
  width: 100%;
  max-height: 420px;
  padding-right: 6px;
  overflow: auto;
}

.permission-group {
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
}

.permission-group-title {
  margin-bottom: 8px;
  color: #334155;
  font-weight: 700;
}

.permission-group :deep(.el-checkbox) {
  min-width: 260px;
  margin-right: 18px;
  margin-bottom: 8px;
}

.pagination-line {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.dialog-footer-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
