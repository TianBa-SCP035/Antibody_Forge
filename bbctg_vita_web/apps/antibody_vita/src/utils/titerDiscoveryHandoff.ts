import {
  fetchElisaPlates,
  fetchFacsPlates,
  fetchSerumDetailByExperimentId,
  skipGlobalErrorHandler,
} from '#/api/serum';
import { saveDiscoveryWorkbench } from '#/api/discoveryWorkbench';
import {
  buildFacsConclusionForPage,
  buildGroupAntigenLabel,
  sortMouseColumns,
  summarizeTiterBrief,
} from '#/utils/serumTiterConclusion';

const LIMIT = {
  mouse_strain_category: 128,
  mouse_strain: 128,
  cage_position: 64,
  mouse_nos: 512,
  immune_antigen: 255,
} as const;

export interface TiterMouseSelection {
  experiment_id?: string;
  cage_position?: string;
  groups?: Array<{ group_id?: string; selected_mouse_nos?: string[] }>;
}

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const value of values) {
    if (!value || seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function joinFit(parts: string[], separator: string, max: number): string {
  const kept: string[] = [];
  for (const part of parts) {
    const next = kept.length ? `${kept.join(separator)}${separator}${part}` : part;
    if (next.length > max) break;
    kept.push(part);
  }
  return kept.join(separator);
}

function codes(value: unknown): string[] {
  const raw = Array.isArray(value)
    ? value.map((item) => text(item))
    : text(value).replace(/，/g, ',').split(',');
  return unique(raw.map((item) => item.trim()).filter(Boolean));
}

function selectedGroups(selection: TiterMouseSelection, project: Record<string, any> | null) {
  const mouseNos: string[] = [];
  const mouseLines: string[] = [];
  const groupIds: string[] = [];
  for (const group of selection.groups || []) {
    const groupId = text(group.group_id);
    const nos = sortMouseColumns(
      (group.selected_mouse_nos || []).map((no) => text(no)).filter(Boolean),
    );
    if (!nos.length) continue;
    if (groupId) groupIds.push(groupId);
    mouseNos.push(...nos);
    mouseLines.push(`${buildGroupAntigenLabel(groupId, project?.steps, project?.antigens)}：${nos.join('、')}`);
  }
  return { groupIds: unique(groupIds), mouseLines, mouseNos: unique(mouseNos) };
}

function groupTexts(project: Record<string, any> | null, groupIds: string[], key: string): string[] {
  const wanted = new Set(groupIds);
  return unique(
    (Array.isArray(project?.mouse_groups) ? project.mouse_groups : [])
      .filter((group) => wanted.has(text(group?.group_id)))
      .map((group) => text(group?.[key]))
      .filter(Boolean),
  );
}

function immuneAntigenNames(project: Record<string, any> | null, groupIds: string[]): string[] {
  const wanted = new Set(groupIds);
  const nameById = new Map<string, string>();
  for (const antigen of Array.isArray(project?.antigens) ? project.antigens : []) {
    const id = text(antigen?.antigen_id);
    const name = text(antigen?.antigen_name);
    if (id && name) nameById.set(id, name);
  }
  const names: string[] = [];
  for (const step of Array.isArray(project?.steps) ? project.steps : []) {
    if (!wanted.has(text(step?.group_id))) continue;
    for (const antigenId of text(step?.antigen_id).split(',').map((item) => item.trim()).filter(Boolean)) {
      const name = nameById.get(antigenId);
      if (name) names.push(name);
    }
  }
  return unique(names);
}

function assemblePayload(
  project: Record<string, any> | null,
  selection: TiterMouseSelection,
  picked: ReturnType<typeof selectedGroups>,
  serumTiter: string,
) {
  return {
    project_code: text(project?.project_code),
    experiment_id: text(project?.experiment_id) || text(selection.experiment_id),
    target_name: text(project?.target_name),
    target_codes: codes(project?.target_codes),
    study_type: text(project?.study_type),
    pm: text(project?.pm),
    mouse_strain_category: joinFit(
      groupTexts(project, picked.groupIds, 'mouse_strain_category'),
      ',',
      LIMIT.mouse_strain_category,
    ),
    mouse_strain: joinFit(
      groupTexts(project, picked.groupIds, 'mouse_strain'),
      ',',
      LIMIT.mouse_strain,
    ),
    cage_position: text(selection.cage_position).slice(0, LIMIT.cage_position),
    mouse_count: picked.mouseNos.length,
    mouse_nos: joinFit(picked.mouseLines, '\n', LIMIT.mouse_nos),
    serum_titer: text(serumTiter),
    immune_antigen: joinFit(immuneAntigenNames(project, picked.groupIds), '、', LIMIT.immune_antigen),
  };
}

export async function handoffTiterToDiscovery(selection: TiterMouseSelection) {
  const experimentId = text(selection.experiment_id);
  if (!experimentId) {
    throw new Error('缺少实验号');
  }
  const [project, facsRes, elisaRes] = await Promise.all([
    fetchSerumDetailByExperimentId(experimentId),
    fetchFacsPlates({ experiment_id: experimentId }, skipGlobalErrorHandler),
    fetchElisaPlates({ experiment_id: experimentId }, skipGlobalErrorHandler),
  ]);
  if (!project?.id) {
    throw new Error('未找到对应的免疫项目');
  }
  const picked = selectedGroups(selection, project);
  const model = buildFacsConclusionForPage(
    project,
    project.titer_targets,
    facsRes?.items || [],
    elisaRes?.items || [],
  );
  return saveDiscoveryWorkbench(
    assemblePayload(project, selection, picked, summarizeTiterBrief(model, picked.mouseNos)),
  );
}
