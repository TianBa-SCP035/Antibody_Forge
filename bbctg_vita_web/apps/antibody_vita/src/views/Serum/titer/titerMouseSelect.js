const PLATE_COLUMNS = 10;
export const PLATE_COLUMN_LIST = Array.from({ length: PLATE_COLUMNS }, (_, i) => i + 1);
const ROW_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export const TITER_MOUSE_IDENTITY_FIELDS = [
  { key: 'project_code', label: '项目编号', kind: 'text' },
  { key: 'target_name', label: '靶点', kind: 'text' },
  { key: 'cage_position', label: '笼位', kind: 'text' },
  { key: 'mouse_count', label: '只数', kind: 'number' },
  { key: 'assay_method', label: '检测方法', kind: 'text' },
  { key: 'facs_plate_count', label: 'FACS', kind: 'number' },
  { key: 'elisa_plate_count', label: 'ELISA', kind: 'number' },
];

function parseLegacyMouseTokens(str) {
  const text = (str || '').trim();
  if (!text) return [];
  const tokens = [];
  for (const part of text.split(/[，\n]+/)) {
    const match = part.match(/^[FM]：(.+)$/);
    const body = match?.[1] || part;
    body.split('、').forEach((token) => {
      const no = token.trim();
      if (no) tokens.push(no);
    });
  }
  return tokens;
}

export function miceInGroup(group) {
  const registry = group?.mouse_registry?.mice;
  if (Array.isArray(registry) && registry.length) {
    return registry
      .map((mouse) => ({
        no: String(mouse?.no || '').trim(),
        alive: mouse?.alive !== false,
      }))
      .filter((mouse) => mouse.no);
  }
  return parseLegacyMouseTokens(group?.mouse_no_list || '').map((no) => ({ no, alive: true }));
}

function mouseSlotNo(rowLabel, column) {
  return `${rowLabel}${String(column).padStart(2, '0')}`;
}

function parseMouseSlotNo(value) {
  const match = String(value || '').match(/^([A-Z])(\d{1,2})$/i);
  if (!match?.[1] || !match[2]) return null;
  const rowIndex = ROW_LABELS.indexOf(match[1].toUpperCase());
  const column = Number.parseInt(match[2], 10);
  return rowIndex >= 0 && column >= 1 && column <= PLATE_COLUMNS
    ? { rowIndex, column }
    : null;
}

export function mouseSlotsInRect(startNo, endNo) {
  const start = parseMouseSlotNo(startNo);
  const end = parseMouseSlotNo(endNo);
  if (!start || !end) return [];
  const result = [];
  const rowMin = Math.min(start.rowIndex, end.rowIndex);
  const rowMax = Math.max(start.rowIndex, end.rowIndex);
  const colMin = Math.min(start.column, end.column);
  const colMax = Math.max(start.column, end.column);
  for (let rowIndex = rowMin; rowIndex <= rowMax; rowIndex += 1) {
    for (let column = colMin; column <= colMax; column += 1) {
      result.push(mouseSlotNo(ROW_LABELS[rowIndex] || '', column));
    }
  }
  return result;
}

function layoutPlateRows(mice) {
  if (!mice.length) return [];
  const rows = [];
  for (let index = 0; index < mice.length; index += PLATE_COLUMNS) {
    const rowIndex = Math.floor(index / PLATE_COLUMNS);
    const rowLabel = ROW_LABELS[rowIndex] || String(rowIndex + 1);
    const cells = [];
    for (let column = 1; column <= PLATE_COLUMNS; column += 1) {
      const mouseIndex = index + column - 1;
      const slotNo = mouseSlotNo(rowLabel, column);
      if (mouseIndex < mice.length) {
        const mouse = mice[mouseIndex];
        cells.push({
          ...mouse,
          mouseIndex,
          slotNo,
          key: `m-${mouseIndex}`,
        });
      } else {
        cells.push({
          no: '',
          alive: false,
          mouseIndex: -1,
          slotNo,
          key: `empty-${rowIndex}-${column}`,
        });
      }
    }
    rows.push({ rowLabel, cells });
  }
  return rows;
}

export function selectionKey(groupId, mouseIndex) {
  return `${groupId}::${mouseIndex}`;
}

export function buildPlateGroup(group, selectedKeys) {
  const groupId = (group.group_id || '').trim();
  if (!groupId) return null;
  const mice = miceInGroup(group);
  if (!mice.length) return null;

  const plateRows = layoutPlateRows(mice);
  const cellBySlot = new Map();
  for (const row of plateRows) {
    for (const cell of row.cells) {
      if (cell.slotNo) cellBySlot.set(cell.slotNo, cell);
    }
  }

  let aliveCount = 0;
  let deadCount = 0;
  let selectedCount = 0;
  mice.forEach((mouse, mouseIndex) => {
    if (mouse.alive) {
      aliveCount += 1;
      if (selectedKeys.has(selectionKey(groupId, mouseIndex))) selectedCount += 1;
    } else {
      deadCount += 1;
    }
  });

  return {
    groupId,
    strain: (group.mouse_strain || '').trim(),
    plateRows,
    cellBySlot,
    aliveCount,
    deadCount,
    selectedCount,
  };
}

export function titerOrderIdentityFields(order) {
  const source = order || {};
  return TITER_MOUSE_IDENTITY_FIELDS.map((field) => ({
    label: field.label,
    value: field.kind === 'number'
      ? (source[field.key] ?? 0)
      : (source[field.key] || '—'),
  }));
}
