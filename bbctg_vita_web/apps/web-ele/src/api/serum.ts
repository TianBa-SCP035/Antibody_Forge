import request from '#/utils/request';

export function fetchStats() {
  return request({
    method: 'get',
    url: '/serum/stats',
  });
}

export function fetchList(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/list',
  });
}

export function fetchDetail(id: any) {
  return request({
    method: 'get',
    params: { id },
    url: '/serum/detail',
  });
}

export function fetchNextId(code: any) {
  return request({
    method: 'get',
    params: { code },
    url: '/serum/next_id',
  });
}

export function saveSerum(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/save',
  });
}

export function deleteSerum(id: any) {
  return request({
    data: { id },
    method: 'post',
    url: '/serum/delete',
  });
}

export function getSerumFilterOptions() {
  return request({
    method: 'get',
    url: '/serum/filter_options',
  });
}

export function updateSerumStatus(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/update_status',
  });
}

export function updateCagePosition(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/update_cage_position',
  });
}

export function export_mouse(data: any) {
  return request({
    data,
    method: 'post',
    responseType: 'blob',
    url: '/serum/export_mouse',
  });
}

export function autoUpdateStatus(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/auto_update_status',
  });
}

export function fetchIndexFiles(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/file/list',
  });
}

export function saveIndexFile(data: any) {
  return request({
    data,
    headers: { 'Content-Type': 'multipart/form-data' },
    method: 'post',
    url: '/serum/titer/file/save',
  });
}

export function deleteIndexFile(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/file/delete',
  });
}

export function renameIndexFile(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/file/rename',
  });
}

export function replaceIndexFile(data: any) {
  return request({
    data,
    headers: { 'Content-Type': 'multipart/form-data' },
    method: 'post',
    url: '/serum/titer/file/replace',
  });
}

export function saveTiterTargets(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/target/save',
  });
}

export function saveTiterPcs(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/pc/save',
  });
}

export function fetchFacsPlates(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/plate/list',
  });
}

export function saveFacsPlate(data: any) {
  return request({
    data,
    method: 'post',
    url: '/serum/titer/plate/save',
  });
}

export function deleteFacsPlate(id: any) {
  return request({
    data: { id },
    method: 'post',
    url: '/serum/titer/plate/delete',
  });
}
