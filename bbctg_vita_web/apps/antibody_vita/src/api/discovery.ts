import { requestClient } from '#/api/request';

type PostConfig = Parameters<typeof requestClient.post>[2];

export interface TargetItem {
  id: number;
  external_id: number;
  snum: string;
  name: string;
  type?: null | number;
  status?: null | number;
  ko_lethal_info?: null | number;
  ko_lethal_info_desc?: null | string;
  structure_feature?: null | string;
  shape_remark?: null | string;
  structure_feature_remark?: null | string;
  ko_mgi?: null | string;
  ko_impc?: null | string;
  effect_cell?: null | string;
  ko_gt?: null | string;
  official_full_name?: null | string;
  human_gene_official_name?: null | string;
  human_gene_alias_name?: null | string;
  human_ncbi_gene_id?: null | string;
  human_chromosome_position?: null | string;
  is_homologous_gene?: boolean | null;
  mouse_gene_official_name?: null | string;
  mouse_gene_alias_name?: null | string;
  mouse_ncbi_gene_id?: null | string;
  mouse_chromosome_position?: null | string;
  human_mouse_homology?: null | string;
  human_dog_homology?: null | string;
  human_cat_homology?: null | string;
  human_monkey_homology?: null | string;
  human_mouse_homology_expect_functional_domain?: null | string;
  gene_functional_desc?: null | string;
  is_ko_affect_humoral_immunity?: boolean | null;
  is_ko_affect_humoral_immunity_desc?: null | string;
  is_human_mouse_cross?: null | string;
  indication?: null | string;
  gene_family?: null | string;
  signal_path?: null | string;
  remark?: null | string;
  is_active: boolean;
  synced_at?: null | string;
}

export interface TargetStats {
  total: number;
  developed: number;
  undeveloped: number;
  unmarked: number;
  synced_at?: null | string;
}

export interface TargetListQuery {
  page: number;
  limit: number;
  keyword?: string;
  status?: '' | '1' | '2' | 'unknown';
  include_inactive?: boolean;
}

export interface TargetListResult {
  items: TargetItem[];
  total: number;
  page: number;
  limit: number;
  stats: TargetStats;
}

export function fetchTargetList(data: TargetListQuery, config?: PostConfig) {
  return requestClient.post<TargetListResult>('/discovery/targets/list', data, config);
}
