/**
 * Read and fill Element Plus forms/tables on the current page through the controls' own
 * v-model handlers, so selects, user pickers, date pickers and table cells behave exactly as if
 * the user had picked the value (page @change side effects included). Never clicks submit/save;
 * on auto-save pages the page itself persists the change, which is why those are flagged.
 *
 * Production Vue builds don't put `__vueParentComponent` on elements, so the element → owner
 * component map is rebuilt from the app root vnode on every scan.
 */

import { isSecretInput, maskContacts, PRIVATE_NAME } from './pageContext';

export type ControlKind =
  | 'text'
  | 'textarea'
  | 'number'
  | 'select'
  | 'date'
  | 'switch'
  | 'radio'
  | 'custom'
  | 'readonly';

type Option = { value: unknown; label: string };

type Control = {
  kind: ControlKind;
  inst: any | null;
  options?: Option[];
  allowCreate?: boolean;
  multiple?: boolean;
  /** Remote-search select: it only holds the options of its last search, so a value has to be searched first. */
  remote?: (query: string) => unknown;
  disabled: boolean;
};

export type FormFieldInfo = {
  field: string;
  required: boolean;
  error?: string;
  control: Control;
  value: string;
};

export type TableInfo = {
  title: string;
  columns: string[];
  /** rows[r][c] — null when the cell has no editable control */
  cells: Array<Array<{ control: Control; value: string } | null>>;
  addButton: HTMLElement | null;
  tabHeader: HTMLElement | null;
};

export type PageForm = {
  fields: FormFieldInfo[];
  tables: TableInfo[];
  /** Label of the page's own save/submit button; null means edits may take effect immediately. */
  saveButton: string | null;
  /** The page saves by itself shortly after a change; applied fills reach the server without a click. */
  autoSave: boolean;
};

export type FillTarget = { table?: string; row?: number; field: string };
export type ResolvedFill = FillTarget & { value: string; reason?: string; display: string };

const LEAF_SELECTOR =
  'input, textarea, .el-select__wrapper, .el-select, .el-switch, .el-radio, .el-checkbox, .el-input-number, .el-date-editor, .el-cascader';

// ---------------- vnode → owner map ----------------

function rootVNodes(): any[] {
  const hosts = new Set<Element>();
  const app = document.querySelector('#app');
  if (app) hosts.add(app);
  for (const el of Array.from(document.body.children)) hosts.add(el);
  return [...hosts].map((el) => (el as any)._vnode).filter(Boolean);
}

function buildOwnerMap(): WeakMap<Element, any> {
  const map = new WeakMap<Element, any>();
  const stack: Array<[any, any]> = rootVNodes().map((vn) => [vn, null] as [any, any]);
  let guard = 0;
  while (stack.length && guard++ < 300_000) {
    const [vn, owner] = stack.pop()!;
    if (!vn || typeof vn !== 'object') continue;
    if (vn.component) {
      stack.push([vn.component.subTree, vn.component]);
      continue;
    }
    if (vn.suspense) {
      stack.push([vn.suspense.activeBranch, owner]);
      continue;
    }
    if (owner && typeof vn.type === 'string' && vn.el instanceof Element && !map.has(vn.el)) {
      map.set(vn.el, owner);
    }
    if (Array.isArray(vn.children)) {
      for (const c of vn.children) stack.push([c, owner]);
    }
  }
  return map;
}

let owners = new WeakMap<Element, any>();

function ownerOf(el: Element | null): any {
  let cur: Element | null = el;
  while (cur) {
    const dev = (cur as any).__vueParentComponent;
    if (dev) return dev;
    const hit = owners.get(cur);
    if (hit) return hit;
    cur = cur.parentElement;
  }
  return null;
}

// ---------------- controls ----------------

function text(v: unknown) {
  return v == null ? '' : String(v).trim();
}

function displayed(el: Element | null): el is HTMLElement {
  if (!(el instanceof HTMLElement) || el.closest('.ff-root')) return false;
  const st = getComputedStyle(el);
  if (st.display === 'none' || st.visibility === 'hidden') return false;
  const r = el.getBoundingClientRect();
  return r.width > 1 && r.height > 1;
}

function vnodeProps(inst: any): Record<string, any> {
  return inst?.vnode?.props || {};
}

function isModelControl(inst: any) {
  const vp = vnodeProps(inst);
  return !!inst?.props && 'modelValue' in inst.props && (vp['onUpdate:modelValue'] || vp.onChange);
}

function selectStates(inst: any) {
  const st = inst?.setupState?.states ?? inst?.exposed?.states;
  return st && (st.options instanceof Map || st.cachedOptions instanceof Map) ? st : null;
}

/** `includeSelf`: the container is the control's own root element (loose controls outside form items). */
function readControl(container: HTMLElement, includeSelf = false): Control {
  const tops = new Set<any>();
  let select: any = null;
  const leaves = Array.from(container.querySelectorAll(LEAF_SELECTOR));
  if (includeSelf && container.matches(LEAF_SELECTOR)) leaves.unshift(container);
  for (const leaf of leaves) {
    let inst = ownerOf(leaf);
    let best: any = null;
    while (inst) {
      const root = inst.vnode?.el as Node | null;
      if (!root || !container.contains(root) || (root === container && !includeSelf)) break;
      if (isModelControl(inst)) best = inst;
      if (!select && selectStates(inst)) select = inst;
      inst = inst.parent;
    }
    if (best) tops.add(best);
  }
  const lockedByPage = !!container.closest('[inert]');
  if (tops.size !== 1) {
    return { kind: tops.size ? 'custom' : 'readonly', inst: null, disabled: true };
  }
  const inst = [...tops][0];
  // Passwords are neither read (they'd go to the models) nor filled.
  if (inst.props?.type === 'password' || inst.props?.showPassword || leaves.some((l) => isSecretInput(l))) {
    return { kind: 'readonly', inst: null, disabled: true };
  }
  // A bound `loading` prop on a switch is the instant-save pattern (feature toggles that call the API on change).
  // Selects are excluded: remote-search selects bind `loading` for their option fetch.
  const instantSave = !select && !!container.querySelector('.el-switch') && 'loading' in vnodeProps(inst);
  const disabled =
    lockedByPage || instantSave || !!inst.props?.disabled || !!inst.props?.readonly || !!select?.props?.disabled;
  if (select) {
    const st = selectStates(select)!;
    const map: Map<unknown, any> = st.options?.size ? st.options : st.cachedOptions;
    const options = [...map.values()].map((o) => ({
      value: o.value,
      label: text(o.currentLabel ?? o.label ?? o.value),
    }));
    return {
      kind: 'select',
      inst,
      options,
      allowCreate: !!select.props?.allowCreate,
      multiple: !!select.props?.multiple || Array.isArray(inst.props.modelValue),
      ...(select.props?.remote && typeof select.props.remoteMethod === 'function'
        ? { remote: (q: string) => select.props.remoteMethod(q) }
        : {}),
      disabled,
    };
  }
  // Time pickers share the date editor's class but take times, which the date conversion would get wrong.
  if (container.querySelector('.el-date-editor--time, .el-date-editor--timerange')) return { kind: 'custom', inst: null, disabled: true };
  if (container.querySelector('.el-date-editor')) return { kind: 'date', inst, disabled };
  if (container.querySelector('.el-input-number')) return { kind: 'number', inst, disabled };
  if (container.querySelector('.el-switch')) return { kind: 'switch', inst, disabled };
  const radios = Array.from(container.querySelectorAll('.el-radio, .el-radio-button'));
  if (radios.length) {
    const options = radios.map((r) => {
      const p = ownerOf(r)?.props || {};
      return { value: p.value ?? p.label, label: text((r as HTMLElement).innerText) };
    });
    return { kind: 'radio', inst, options, disabled };
  }
  const boxes = container.querySelector('.el-checkbox-group') ? Array.from(container.querySelectorAll('.el-checkbox')) : [];
  if (boxes.length) {
    const options = boxes.map((b) => {
      const p = ownerOf(b)?.props || {};
      return { value: p.value ?? p.label, label: text((b as HTMLElement).innerText) || text(p.label) };
    });
    return { kind: 'select', inst, options, multiple: true, disabled };
  }
  if (container.querySelector('.el-checkbox')) return { kind: 'switch', inst, disabled };
  if (container.querySelector('textarea')) return { kind: 'textarea', inst, disabled };
  return { kind: 'text', inst, disabled };
}

function displayValue(c: Control): string {
  const v = c.inst?.props?.modelValue;
  const one = (x: unknown) => {
    if (x instanceof Date) return x.toISOString().slice(0, 10);
    if (typeof x === 'boolean') return x ? '开' : '关';
    const opt = c.options?.find((o) => o.value === x);
    return opt ? opt.label : text(x);
  };
  if (Array.isArray(v)) return v.map(one).filter(Boolean).join('、');
  return one(v);
}

// ---------------- scanning ----------------

function formRoot(): ParentNode {
  const overlays = Array.from(document.querySelectorAll('.el-dialog, .el-drawer')).filter(displayed);
  return (overlays[overlays.length - 1] as HTMLElement | undefined) || document;
}

const HEADISH = /(^|[-_\s])(head|header|title|toolbar|bar)([-_\s]|$)/i;

/**
 * Section header for a table: the el-card header, or the nearest header-like block that precedes the
 * table inside one of its ancestors (e.g. `<section><div class="panel-head">…</div><el-table/></section>`).
 */
function sectionHeader(table: Element): HTMLElement | null {
  const cardHead = table.closest('.el-card')?.querySelector(':scope > .el-card__header') as HTMLElement | null;
  let cur: Element | null = table;
  for (let depth = 0; depth < 4 && cur?.parentElement; depth += 1) {
    const parent: Element = cur.parentElement;
    if (cardHead && parent === cardHead.parentElement) return cardHead;
    for (const sib of Array.from(parent.children)) {
      if (sib === cur) break;
      if (sib.contains(table) || !displayed(sib)) continue;
      if (/^H[1-5]$/.test(sib.tagName) || HEADISH.test(sib.className || '')) return sib as HTMLElement;
    }
    cur = parent;
  }
  return cardHead;
}

function headerText(head: HTMLElement | null): string {
  if (!head) return '';
  const titled = head.querySelector('[class*="title"]') as HTMLElement | null;
  const span = titled || (head.querySelector('span') as HTMLElement | null);
  return text(span?.innerText || head.innerText.split('\n')[0]).slice(0, 40);
}

function tabFor(table: Element): { label: string; header: HTMLElement | null } {
  const pane = table.closest('.el-tab-pane');
  if (!pane?.id) return { label: '', header: null };
  const header = document.getElementById(pane.id.replace(/^pane-/, 'tab-'));
  return { label: text(header?.innerText), header };
}

/** What the user would call a table: its card / section heading plus the tab it sits in. */
export function tableTitleOf(table: Element, head: HTMLElement | null = sectionHeader(table)): string {
  const tab = tabFor(table);
  const headTitle = headerText(head);
  return [headTitle, headTitle.includes(tab.label) ? '' : tab.label].filter(Boolean).join(' · ');
}

const ADD_ROW = /^(添加|新增|增加|新建)\s*[\u4E00-\u9FA5A-Za-z0-9 ]{1,8}$/;

function addButtonFor(head: HTMLElement | null): HTMLElement | null {
  if (!head) return null;
  const buttons = Array.from(head.querySelectorAll('button')).filter((b) => {
    const t = text((b as HTMLElement).innerText);
    return ADD_ROW.test(t) && !/保存|提交|删除|导入|导出|下发/.test(t) && !(b as HTMLButtonElement).disabled;
  });
  return buttons.length === 1 ? (buttons[0] as HTMLElement) : null;
}

function tableVisible(table: Element) {
  if (displayed(table)) return true;
  const tabs = table.closest('.el-tabs');
  return !!tabs && displayed(tabs);
}

/** Paginated tables are data lists (rows are saved records), never form input. */
function isDataList(table: Element) {
  let cur: Element | null = table.parentElement;
  for (let depth = 0; depth < 3 && cur; depth += 1, cur = cur.parentElement) {
    if (cur.querySelector(':scope > .el-pagination, :scope > * > .el-pagination')) return true;
  }
  return false;
}

const SAVE_BUTTON = /^(保存|提交|确定|确认|创建|暂存|更新|下发)/;

/** Popovers (rename bubbles etc.) carry their own small 保存 button; it doesn't make the page a save-later form. */
function findSaveButton(root: ParentNode): string | null {
  for (const b of Array.from(root.querySelectorAll('button'))) {
    if (b.closest('.ff-root, .el-table, .el-message-box, .el-popper, .el-popover') || !displayed(b)) continue;
    if ((b as HTMLButtonElement).disabled) continue;
    const t = text((b as HTMLElement).innerText);
    if (t.length <= 8 && SAVE_BUTTON.test(t)) return t;
  }
  return null;
}

const AUTO_SAVE_KEY = /auto_?sav|^persist/i;

/** A short visible label such as「自动保存」/「已自动保存」next to the form (not the pet's own cards). */
function hasAutoSaveLabel(root: ParentNode): boolean {
  const walker = document.createTreeWalker(root as Node, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const t = node.textContent || '';
    if (!t.includes('自动保存') || t.trim().length > 16) continue;
    const el = node.parentElement;
    if (el && !el.closest('.ff-root, .el-message, .el-notification') && displayed(el)) return true;
  }
  return false;
}

/** Auto-saving pages write to the server a few seconds after any change, so "not saved yet" isn't true there. */
function detectAutoSave(root: ParentNode, sample: any): boolean {
  if (root.querySelector('[title*="自动保存"]') || hasAutoSaveLabel(root)) return true;
  for (let cur = sample, depth = 0; cur && depth < 40; cur = cur.parent, depth += 1) {
    const keys = [
      ...Object.keys(cur.data || {}),
      ...Object.keys(cur.setupState || {}),
      ...Object.keys(cur.type?.methods || {}),
    ];
    if (keys.some((k) => AUTO_SAVE_KEY.test(k))) return true;
  }
  return false;
}

const CONTROL_ROOTS = '.el-input, .el-textarea, .el-select, .el-date-editor, .el-input-number, .el-switch, .el-radio-group, .el-cascader';

/** Label for a control that isn't inside an el-form-item: wrapping <label>, a short text sibling, or the placeholder. */
function looseLabel(el: HTMLElement): string {
  const clean = (s: string) =>
    text(s)
      .replace(/^\*\s*/, '')
      .replace(/[:：]\s*$/, '')
      .replace(/[（(](可选|选填|必填)[）)]$/, '')
      .trim();
  const wrap = el.closest('label');
  if (wrap) {
    const own = Array.from(wrap.children).find((c) => c !== el && !c.contains(el) && text((c as HTMLElement).innerText));
    if (own) return clean((own as HTMLElement).innerText);
  }
  let cur: HTMLElement | null = el;
  for (let depth = 0; depth < 2 && cur; depth += 1, cur = cur.parentElement) {
    const prev = cur.previousElementSibling as HTMLElement | null;
    const t = prev && !prev.querySelector(CONTROL_ROOTS) ? clean(prev.innerText) : '';
    if (t && t.length <= 12) return t;
  }
  const input = el.querySelector('input, textarea') as HTMLInputElement | null;
  const hint = input?.getAttribute('aria-label') || input?.placeholder || '';
  return clean(hint.replace(/^(请输入|请选择|输入|选择)/, '')).slice(0, 20);
}

/** Field labels of the form on screen, to tell whether a fill card still belongs to it. */
export function formLabels(form: PageForm = scanPageForm()): string[] {
  return form.fields.map((f) => f.field);
}

/**
 * Same form as when the card was made? Mostly the same labels (a tab switch hides a few) — a different dialog
 * opened on the same URL shares few of them.
 */
export function sameForm(before: string[] | undefined, now: string[]): boolean {
  if (!before?.length) return true;
  const had = new Set(before);
  const shared = now.filter((label) => had.has(label)).length;
  return shared / new Set([...before, ...now]).size >= 0.6;
}

export function scanPageForm(): PageForm {
  owners = buildOwnerMap();
  const root = formRoot();
  const fields: FormFieldInfo[] = [];
  for (const item of Array.from(root.querySelectorAll('.el-form-item'))) {
    if (!displayed(item) || item.parentElement?.closest('.el-form-item')) continue;
    if (item.closest('.el-table')) continue;
    const label = text((item.querySelector('.el-form-item__label') as HTMLElement | null)?.innerText)
      .replace(/^\*\s*/, '')
      .replace(/[:：]\s*$/, '');
    if (!label) continue;
    const content = (item.querySelector('.el-form-item__content') as HTMLElement | null) || (item as HTMLElement);
    const control = readControl(content);
    const shownValue = control.inst ? displayValue(control) : text(content.innerText).slice(0, 80);
    fields.push({
      field: label.slice(0, 40),
      required: item.classList.contains('is-required'),
      error: text((item.querySelector('.el-form-item__error') as HTMLElement | null)?.innerText) || undefined,
      control,
      value: shownValue && PRIVATE_NAME.test(label) ? '(已隐藏)' : maskContacts(shownValue),
    });
    if (fields.length >= 60) break;
  }

  const seen = new Set(fields.map((f) => f.field));
  for (const el of Array.from(root.querySelectorAll(CONTROL_ROOTS)) as HTMLElement[]) {
    if (fields.length >= 60) break;
    if (el.parentElement?.closest(CONTROL_ROOTS) || el.closest('.el-form-item, .el-table, .ff-root, .el-popper')) continue;
    if (!displayed(el)) continue;
    const control = readControl(el, true);
    if (!control.inst) continue;
    let label = looseLabel(el);
    if (!label) continue;
    for (let n = 2; seen.has(label); n += 1) label = `${label.replace(/#\d+$/, '')}#${n}`;
    seen.add(label);
    fields.push({ field: label.slice(0, 40), required: false, control, value: displayValue(control) });
  }

  const tables: TableInfo[] = [];
  for (const table of Array.from(root.querySelectorAll('.el-table'))) {
    if (!tableVisible(table) || table.closest('.ff-root') || isDataList(table)) continue;
    const columns = Array.from(table.querySelectorAll('.el-table__header-wrapper thead tr:last-child th')).map((th) =>
      text((th as HTMLElement).innerText),
    );
    const rows = Array.from(table.querySelectorAll('.el-table__body-wrapper tbody > tr.el-table__row'));
    const cells = rows.slice(0, 30).map((tr) =>
      Array.from(tr.children).map((td) => {
        const cell = (td.querySelector('.cell') as HTMLElement | null) || (td as HTMLElement);
        if (!cell.querySelector(LEAF_SELECTOR)) return null;
        const control = readControl(cell);
        return control.inst ? { control, value: displayValue(control) } : null;
      }),
    );
    const hasEditable = cells.some((r) => r.some(Boolean));
    const head = sectionHeader(table);
    const addButton = addButtonFor(head);
    if (!hasEditable && !addButton) continue;
    const title = tableTitleOf(table, head) || `表格${tables.length + 1}`;
    tables.push({ title, columns, cells, addButton, tabHeader: tabFor(table).header });
    if (tables.length >= 8) break;
  }
  const sample = fields.find((f) => f.control.inst)?.control.inst ?? tables[0]?.cells.flat().find(Boolean)?.control.inst;
  return { fields, tables, saveButton: findSaveButton(root), autoSave: detectAutoSave(root, sample) };
}

// ---------------- describe for the model ----------------

function controlMeta(c: Control) {
  const meta: Record<string, unknown> = { kind: c.kind };
  if (c.options?.length) meta.options = c.options.slice(0, 25).map((o) => o.label);
  if (c.allowCreate) meta.allow_custom = true;
  if (c.multiple) meta.multiple = true;
  if (c.remote) meta.remote_search = true;
  return meta;
}

function fillableKind(c: Control) {
  return !c.disabled && c.kind !== 'custom' && c.kind !== 'readonly';
}

export function describePageForm(form: PageForm) {
  const issues: Array<Record<string, string>> = [];
  const fields = form.fields.map((f) => {
    if (f.error) issues.push({ field: f.field, issue: `页面校验提示：${f.error}` });
    else if (f.required && !f.value && !f.control.disabled) issues.push({ field: f.field, issue: '必填但为空' });
    const out: Record<string, unknown> = { field: f.field, value: f.value, ...controlMeta(f.control) };
    if (f.required) out.required = true;
    if (!fillableKind(f.control)) out.fillable = false;
    return out;
  });
  const tables = form.tables.map((t) => {
    const editableCols = t.columns
      .map((name, i) => ({ name, i, sample: t.cells.find((r) => r[i])?.[i] }))
      .filter((c) => c.name && c.sample);
    const cols = editableCols.map((c) => ({ name: c.name, ...controlMeta(c.sample!.control) }));
    const rows = t.cells.map((r) => editableCols.map((c) => r[c.i]?.value ?? ''));
    return {
      table: t.title,
      columns: cols.length ? cols : t.columns.filter(Boolean),
      row_count: t.cells.length,
      rows: rows.slice(0, 15),
      can_add_rows: !!t.addButton,
    };
  });
  const emptyFields = form.fields.filter((f) => fillableKind(f.control) && !f.value).length;
  const parts = [
    ...(form.fields.length ? [{ part: '基本信息', empty_fields: emptyFields }] : []),
    ...form.tables.map((t) => ({ part: t.title, rows: t.cells.length, can_add_rows: !!t.addButton })),
  ];
  const editable = !!form.saveButton;
  const note = !editable
    ? '页面上没有保存/提交按钮，改动可能立即生效，不支持代填'
    : form.autoSave
      ? '这个页面会自动保存：用户在卡片上点应用后几秒内就会写进系统（卡片可撤销）。回答里要提醒用户这一点'
      : `填完后由用户自己点「${form.saveButton}」`;
  return {
    editable,
    ...(editable ? { save_button: form.saveButton } : {}),
    ...(form.autoSave ? { auto_save: true } : {}),
    note,
    parts,
    field_count: fields.length,
    fields,
    tables,
    issues,
  };
}

// ---------------- resolve + apply ----------------

function norm(s: string) {
  return s.replace(/\s+/g, '').toLowerCase();
}

function matchName<T>(items: T[], key: string, nameOf: (t: T) => string): T | undefined {
  const k = norm(key);
  if (!k) return undefined;
  return (
    items.find((x) => norm(nameOf(x)) === k) ||
    items.find((x) => norm(nameOf(x)).includes(k)) ||
    items.find((x) => k.includes(norm(nameOf(x))) && norm(nameOf(x)).length >= 2)
  );
}

function findTable(form: PageForm, key: string) {
  const direct = matchName(form.tables, key, (t) => t.title);
  if (direct) return direct;
  const tokens = key.split(/[\s·,，/|-]+/).map(norm).filter(Boolean);
  return tokens.length ? form.tables.find((t) => tokens.every((tk) => norm(t.title).includes(tk))) : undefined;
}

function columnIndex(table: TableInfo, field: string) {
  const exact = table.columns.findIndex((n) => norm(n) === norm(field));
  if (exact >= 0) return exact;
  return table.columns.findIndex((n) => n && (norm(n).includes(norm(field)) || norm(field).includes(norm(n))));
}

type Converted = { ok: true; value: unknown; display: string } | { ok: false; why: string };

/** Values of a multi-select; option labels may themselves contain a separator ("Human CD74 Protein, Fc Tag"). */
const MULTI_SEP = /[,，、;；]/;

function multiParts(v: string, options: Option[] = []): string[] {
  const found: Array<{ at: number; label: string }> = [];
  const taken = Array.from(v, () => false);
  const free = (i: number) => i < 0 || i >= v.length || MULTI_SEP.test(v[i]!) || /\s/.test(v[i]!);
  for (const o of [...options].sort((a, b) => b.label.length - a.label.length)) {
    if (!o.label) continue;
    for (let at = v.indexOf(o.label); at >= 0; at = v.indexOf(o.label, at + 1)) {
      const end = at + o.label.length;
      if (!free(at - 1) || !free(end) || taken.slice(at, end).some(Boolean)) continue;
      found.push({ at, label: o.label });
      taken.fill(true, at, end);
      break;
    }
  }
  const others: Array<{ at: number; label: string }> = [];
  let start = 0;
  for (let i = 0; i <= v.length; i += 1) {
    if (i < v.length && !taken[i] && !MULTI_SEP.test(v[i]!)) continue;
    const label = text(v.slice(start, i));
    if (label) others.push({ at: start, label });
    start = i + 1;
  }
  return [...found, ...others].sort((a, b) => a.at - b.at).map((x) => x.label);
}

export function convertValue(c: Control, raw: string): Converted {
  const v = text(raw);
  switch (c.kind) {
    case 'text':
    case 'textarea':
      return { ok: true, value: raw, display: raw };
    case 'number': {
      const n = Number(v);
      return Number.isFinite(n) ? { ok: true, value: n, display: v } : { ok: false, why: '需要数字' };
    }
    case 'date': {
      const type = c.inst?.props?.type || 'date';
      if (type !== 'date' && type !== 'datetime') return { ok: false, why: '日期范围需要手动选' };
      if (!/^\d{4}-\d{2}-\d{2}/.test(v)) return { ok: false, why: '日期格式需为 YYYY-MM-DD' };
      const fmt = c.inst?.props?.valueFormat;
      return { ok: true, value: fmt ? v.slice(0, Math.max(10, String(fmt).length)) : new Date(v), display: v };
    }
    case 'switch': {
      const on = /^(开|是|true|1|启用|yes)$/i.test(v);
      const p = c.inst?.props || {};
      return { ok: true, value: on ? (p.activeValue ?? true) : (p.inactiveValue ?? false), display: on ? '开' : '关' };
    }
    case 'radio':
    case 'select': {
      const parts = c.multiple ? multiParts(v, c.options) : [v];
      const values: unknown[] = [];
      const labels: string[] = [];
      for (const p of parts) {
        const opt =
          c.options?.find((o) => o.label === p || text(o.value) === p) ||
          c.options?.find((o) => norm(o.label) === norm(p));
        if (opt) {
          values.push(opt.value);
          labels.push(opt.label);
        } else if (c.allowCreate) {
          values.push(p);
          labels.push(p);
        } else if (c.remote) {
          return { ok: false, why: `「${p}」要先在下拉里搜索` };
        } else {
          const labels = (c.options || []).map((o) => o.label).slice(0, 15);
          return { ok: false, why: labels.length ? `「${p}」不在可选项里，可选：${labels.join('、')}` : `「${p}」需要在下拉里搜索后手动选` };
        }
      }
      return { ok: true, value: c.multiple ? values : values[0], display: labels.join('、') };
    }
    default:
      return { ok: false, why: '这个字段是自定义控件，需要手动填' };
  }
}

/** Validate one suggestion against the current page; rows past the end are OK when the table can add rows. */
export function resolveFill(
  form: PageForm,
  f: FillTarget & { value: string },
): { ok: true; display: string; unchanged?: boolean } | { ok: false; why: string; manual?: boolean } {
  if (!form.saveButton) return { ok: false, why: '页面没有保存/提交按钮，改动可能立即生效，不代填', manual: true };
  if (!f.table) {
    const field = matchName(form.fields, f.field, (x) => x.field);
    if (!field) return { ok: false, why: '当前表单里没有这个字段' };
    if (!fillableKind(field.control)) return { ok: false, why: field.control.disabled ? '字段不可编辑' : '自定义控件，需要手动填', manual: true };
    const c = convertValue(field.control, f.value);
    if (!c.ok && field.control.remote) return { ok: true, display: text(f.value) };
    return c.ok ? { ok: true, display: c.display, unchanged: c.display === field.value } : { ok: false, why: c.why, manual: c.why.includes('手动') };
  }
  const table = findTable(form, f.table);
  if (!table) {
    const titles = form.tables.map((t) => t.title);
    return {
      ok: false,
      why:
        `没有叫「${f.table}」的表格${titles.length ? `（现有：${titles.join('、')}）` : ''}。` +
        '有的表格要等前面的内容生效后才出现（比如按上面某个表的行生成的页签、选了类型才展开的子表）：这种情况先请用户应用当前卡片，再让你继续',
    };
  }
  const col = columnIndex(table, f.field);
  if (col < 0) return { ok: false, why: `表格「${table.title}」没有「${f.field}」列` };
  const row = Math.floor(Number(f.row) || 0);
  if (row < 1) return { ok: false, why: '表格字段需要 row（从 1 开始）' };
  const sample = table.cells[row - 1]?.[col] ?? table.cells.find((r) => r[col])?.[col];
  if (row > table.cells.length) {
    if (!table.addButton) return { ok: false, why: '这个表格不能自动加行，请先手动添加' };
    if (row > table.cells.length + 10) return { ok: false, why: '一次最多新增 10 行' };
  }
  if (!sample) return row > table.cells.length ? { ok: true, display: f.value } : { ok: false, why: '这一格不可编辑', manual: true };
  if (!fillableKind(sample.control)) return { ok: false, why: '这一列需要手动填', manual: true };
  const c = convertValue(sample.control, f.value);
  if (!c.ok && sample.control.remote) return { ok: true, display: text(f.value) };
  if (!c.ok) return { ok: false, why: c.why, manual: c.why.includes('手动') };
  return { ok: true, display: c.display, unchanged: row <= table.cells.length && c.display === sample.value };
}

function call(handler: unknown, ...args: unknown[]) {
  const list = Array.isArray(handler) ? handler : [handler];
  for (const h of list) if (typeof h === 'function') h(...args);
}

function emitValue(c: Control, value: unknown) {
  const vp = vnodeProps(c.inst);
  call(vp.onFocus, new FocusEvent('focus'));
  call(vp['onUpdate:modelValue'], value);
  call(vp.onChange, value);
  call(vp.onBlur, new FocusEvent('blur'));
}

const sleep = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

async function ensureRows(title: string, need: number): Promise<boolean> {
  let table = findTable(scanPageForm(), title);
  if (!table) return false;
  if (table.cells.length >= need) return true;
  if (!table.addButton) return false;
  if (table.tabHeader) {
    table.tabHeader.click();
    await sleep(80);
  }
  const missing = need - table.cells.length;
  for (let i = 0; i < missing; i += 1) {
    table.addButton.click();
    await sleep(30);
  }
  for (let i = 0; i < 30; i += 1) {
    await sleep(60);
    table = findTable(scanPageForm(), title);
    if (table && table.cells.length >= need) return true;
  }
  return false;
}

/**
 * Run the select's own remote search for the value and wait for its options to come back; returns the control
 * as it is after the search with the converted value, or null when the search never offered it.
 */
async function searchFor(f: ResolvedFill): Promise<{ control: Control; converted: Converted & { ok: true } } | null> {
  const hit = locate(scanPageForm(), f);
  if (!hit?.control.remote) return null;
  const parts = hit.control.multiple ? multiParts(text(f.value), hit.control.options) : [text(f.value)];
  // A search replaces the options, so only one searched value can be picked at a time.
  if (parts.length !== 1) return null;
  hit.control.remote(parts[0]!);
  for (let i = 0; i < 30; i += 1) {
    await sleep(100);
    const now = locate(scanPageForm(), f);
    if (!now) return null;
    const c = convertValue(now.control, f.value);
    if (c.ok) return { control: now.control, converted: c };
  }
  return null;
}

/** Current control + display value of a fill target, or null when it can't be found. */
function locate(form: PageForm, f: FillTarget): { control: Control; value: string } | null {
  if (!f.table) return matchName(form.fields, f.field, (x) => x.field) ?? null;
  const table = findTable(form, f.table);
  const col = table ? columnIndex(table, f.field) : -1;
  return table && col >= 0 ? (table.cells[(f.row || 0) - 1]?.[col] ?? null) : null;
}

function currentDisplay(form: PageForm, f: ResolvedFill): string | null {
  return locate(form, f)?.value ?? null;
}

/** What a field held before we wrote it, so the user can undo a whole card. */
export type FillSnapshot = { fill: ResolvedFill; prev: unknown; addedRow: boolean };

function fillLabel(f: FillTarget) {
  return f.table ? `${f.table}第${f.row}行·${f.field}` : f.field;
}

function modelValue(c: Control): unknown {
  const v = vnodeProps(c.inst).modelValue;
  return Array.isArray(v) ? [...v] : v;
}

function controlEl(c: Control): HTMLElement | null {
  const el = c.inst?.vnode?.el ?? c.inst?.subTree?.el;
  if (el instanceof HTMLElement) return el;
  return el?.nextElementSibling instanceof HTMLElement ? el.nextElementSibling : null;
}

/** Briefly outline the fields that changed so the user can see what to review before saving. */
function highlight(fills: ResolvedFill[]) {
  const form = scanPageForm();
  for (const f of fills) {
    const hit = locate(form, f);
    const el = hit && controlEl(hit.control);
    el?.animate(
      [
        { outline: '2px solid rgba(56, 189, 248, 0.95)', outlineOffset: '1px' },
        { outline: '2px solid rgba(56, 189, 248, 0.95)', outlineOffset: '1px', offset: 0.7 },
        { outline: '2px solid rgba(56, 189, 248, 0)', outlineOffset: '1px' },
      ],
      { duration: 3200, easing: 'ease-out' },
    );
  }
}

export async function applyFills(fills: ResolvedFill[]): Promise<{
  applied: string[];
  missed: string[];
  overridden: Array<{ label: string; now: string }>;
  snapshots: FillSnapshot[];
}> {
  const snapshots: FillSnapshot[] = [];
  const pass = await applyOnce(fills, snapshots);
  // Page watchers can rewrite a field after a later one changes (e.g. project name regenerated from the target type):
  // put the user's confirmed value back once, then report whatever the page still insists on.
  await sleep(120);
  const done = new Set(pass.applied);
  const drifted = () => {
    const form = scanPageForm();
    return fills.filter((f) => done.has(fillLabel(f)) && norm(currentDisplay(form, f) ?? f.display) !== norm(f.display));
  };
  const first = drifted();
  if (first.length) {
    await applyOnce(first);
    await sleep(120);
  }
  const form = scanPageForm();
  const overridden = drifted().map((f) => ({ label: fillLabel(f), now: currentDisplay(form, f) || '空' }));
  const lost = new Set(overridden.map((o) => o.label));
  highlight(fills.filter((f) => done.has(fillLabel(f)) && !lost.has(fillLabel(f))));
  return { applied: pass.applied.filter((l) => !lost.has(l)), missed: pass.missed, overridden, snapshots };
}

/**
 * Put snapshotted fields back. Rows we added can't be removed safely, so they're reported instead; a field
 * the user (or the page) has changed since the fill is left alone so undo never wipes their later edits.
 */
export async function undoFills(
  snapshots: FillSnapshot[],
): Promise<{ restored: number; skipped: string[]; changedSince: string[] }> {
  const skipped: string[] = [];
  const changedSince: string[] = [];
  let restored = 0;
  for (const s of [...snapshots].reverse()) {
    const form = scanPageForm();
    const hit = s.addedRow ? null : locate(form, s.fill);
    if (!hit || !fillableKind(hit.control)) {
      skipped.push(fillLabel(s.fill));
      continue;
    }
    if (norm(currentDisplay(form, s.fill) ?? '') !== norm(s.fill.display)) {
      changedSince.push(fillLabel(s.fill));
      continue;
    }
    emitValue(hit.control, s.prev);
    restored += 1;
    await sleep(20);
  }
  return { restored, skipped, changedSince };
}

async function applyOnce(
  fills: ResolvedFill[],
  snapshots?: FillSnapshot[],
): Promise<{ applied: string[]; missed: string[] }> {
  const applied: string[] = [];
  const missed: string[] = [];
  if (!scanPageForm().saveButton) return { applied, missed: fills.map(fillLabel) };

  const formFills = fills.filter((f) => !f.table);
  if (formFills.length) {
    const form = scanPageForm();
    for (const f of formFills) {
      const field = matchName(form.fields, f.field, (x) => x.field);
      let control = field?.control;
      let c = control && fillableKind(control) ? convertValue(control, f.value) : null;
      if (control && c && !c.ok && control.remote) {
        const found = await searchFor(f);
        if (found) ({ control, converted: c } = found);
      }
      if (!control || !c?.ok) {
        missed.push(fillLabel(f));
        continue;
      }
      snapshots?.push({ fill: f, prev: modelValue(control), addedRow: false });
      emitValue(control, c.value);
      applied.push(fillLabel(f));
    }
    await sleep(60);
  }

  const byTable = new Map<string, ResolvedFill[]>();
  for (const f of fills.filter((x) => x.table)) {
    const key = findTable(scanPageForm(), f.table!)?.title || f.table!;
    byTable.set(key, [...(byTable.get(key) || []), f]);
  }
  for (const [title, list] of byTable) {
    const need = Math.max(...list.map((f) => f.row || 0));
    const hadRows = findTable(scanPageForm(), title)?.cells.length ?? 0;
    if (!(await ensureRows(title, need))) {
      missed.push(...list.map(fillLabel));
      continue;
    }
    for (const f of list) {
      const table = findTable(scanPageForm(), title);
      const col = table ? columnIndex(table, f.field) : -1;
      const cell = table && col >= 0 ? table.cells[(f.row || 0) - 1]?.[col] : null;
      let control = cell?.control;
      let c = control && fillableKind(control) ? convertValue(control, f.value) : null;
      if (control && c && !c.ok && control.remote) {
        const found = await searchFor(f);
        if (found) ({ control, converted: c } = found);
      }
      if (!control || !c?.ok) {
        missed.push(fillLabel(f));
        continue;
      }
      snapshots?.push({ fill: f, prev: modelValue(control), addedRow: (f.row || 0) > hadRows });
      emitValue(control, c.value);
      applied.push(fillLabel(f));
      await sleep(20);
    }
  }
  return { applied, missed };
}
