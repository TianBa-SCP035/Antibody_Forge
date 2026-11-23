import type { RouteRecordStringComponent } from '@vben/types';

import { requestClient } from '#/api/request';

export async function getAllMenusApi() {
  return requestClient.get<RouteRecordStringComponent[]>('/menu/all');
}
