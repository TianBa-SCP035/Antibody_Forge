/**
 * 像用户一样看和操作任意页面：把可见的可操作元素编号列出来，按编号点击、输入、选择、滚动、截图。
 *
 * 不认识具体模块，只认通用的 DOM 和 Element Plus 结构，新页面不用适配。
 * 操作期间页面若要向后端提交（非查询请求），请求先暂停，由用户在卡片上放行或拦下（见 apiWatch 的 setWriteHold）。
 * 浏览器不允许脚本移动真实鼠标；看得见的指针和宠物跟随由 setPointer 注册的界面负责。
 */

import { pendingRequests, setWriteHold } from './apiWatch';
import { isSecretInput, maskContacts, PRIVATE_NAME } from './pageContext';
import { readPageTables } from './pageTable';

export type Pointer = {
  /** 指针移到元素上并高亮；返回后再真正操作。 */
  show: (el: Element, label: string, kind: PointerKind) => Promise<void>;
  /** 本次操作结束。 */
  done: () => void;
  /** 这一轮结束；immediate：用户停下或接手，马上收起。 */
  end: (immediate: boolean) => void;
};
export type PointerKind = 'click' | 'type' | 'point' | 'look' | 'hover' | 'drag';
export type WriteResult = { status: number; text: string };
/** auto：用户已选「本轮都放行」，界面只需告知，不用再问；result 在放行的请求返回后兑现。 */
export type HeldWrite = { method: string; path: string; kind: string; body: string; trigger: string; auto: boolean; result: Promise<WriteResult>; turn: number };

const MAX_LINES = 220;
const AFTER_ACTION_LINES = 120;
const SETTLE_QUIET_MS = 350;
/** 页面请求还没回来时最多等这么久；一般几百毫秒就静下来了。 */
const SETTLE_MAX_MS = 10_000;
/** 提交被暂停后，等用户在卡片上决定的上限；超时就把“还在等”如实告诉模型。 */
const HELD_WAIT_MS = 120_000;
/** 自动保存这类防抖提交会晚于点击发出，最后一次操作后这段时间内的提交仍要确认。 */
const GUARD_TAIL_MS = 6000;

let pointer: Pointer | null = null;
let onHeldWrite: ((w: HeldWrite) => Promise<boolean>) | null = null;

export function setPointer(p: Pointer | null) {
  pointer = p;
}

export function setHeldWriteHandler(fn: ((w: HeldWrite) => Promise<boolean>) | null) {
  onHeldWrite = fn;
  for (const type of ['pointerdown', 'keydown']) {
    if (fn) window.addEventListener(type, noteHuman, true);
    else window.removeEventListener(type, noteHuman, true);
  }
}

/** 用户自己最近一次在页面上按下鼠标或键盘的时间。宠物派发的事件 isTrusted 为 false，宠物自己的界面不算。 */
let humanAt = 0;
/** 紧跟在用户真实操作后发出的提交算用户自己的，不拦。 */
const HUMAN_WRITE_MS = 2000;
const MODIFIER_KEYS = new Set(['Shift', 'Control', 'Alt', 'Meta', 'CapsLock']);

function noteHuman(e: Event) {
  if (!e.isTrusted || (e instanceof KeyboardEvent && MODIFIER_KEYS.has(e.key))) return;
  if (e.target instanceof Element && ownUi(e.target)) return;
  humanAt = Date.now();
  // 这一轮宠物动过页面后用户动手，就是接手了：两边同时点会互相打架（关掉对方的菜单、抢焦点）。
  if (actedThisTurn && turnSignal && !turnSignal.aborted) onTakeover?.();
}

// ---------------------------------------------------------------- 编号

const refOf = new WeakMap<Element, string>();
const byRef = new Map<string, WeakRef<Element>>();
let refSeq = 0;

function refFor(el: Element): string {
  let ref = refOf.get(el);
  if (!ref) {
    ref = `e${++refSeq}`;
    refOf.set(el, ref);
  }
  if (!byRef.has(ref)) byRef.set(ref, new WeakRef(el));
  return ref;
}

/** 单页应用来回切换会留下大量已删除元素的编号；元素重新挂回来时 refFor 会补上。 */
function pruneRefs() {
  if (byRef.size < 2000) return;
  for (const [ref, weak] of byRef) if (!weak.deref()?.isConnected) byRef.delete(ref);
}

function resolve(ref: string): Element | string {
  const el = byRef.get(String(ref || '').trim())?.deref();
  if (!el || !el.isConnected) return `编号 ${ref} 已失效（页面变了），先 read_page 拿新编号`;
  if (!visible(el)) return `编号 ${ref} 现在看不见（可能被收起或换了页签），先 read_page`;
  return el;
}

// ---------------------------------------------------------------- 读页面

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n)}…` : s);
const squash = (s: string | null | undefined) => (s || '').replace(/\s+/g, ' ').trim();

function ownUi(el: Element) {
  return !!el.closest('.ff-root, #unsupported-browser, #__app-loading__');
}

function visible(el: Element): boolean {
  if (!(el instanceof HTMLElement) || ownUi(el)) return false;
  if (el.closest('[aria-hidden="true"]')) return false;
  const st = getComputedStyle(el);
  if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) return false;
  const r = el.getBoundingClientRect();
  return r.width >= 2 && r.height >= 2;
}

type Kind =
  | '按钮' | '链接' | '页签' | '菜单' | '输入框' | '下拉框' | '日期' | '勾选' | '单选' | '开关' | '选项' | '分页' | '树节点' | '折叠项'
  | '可点' | '可拖';
/** 这些是最小操作单位，里面的子元素不再单独列。「可点」是按样式认出的，可能是整行或卡片，里面的按钮照列。 */
const LEAF: ReadonlySet<Kind> = new Set(['按钮', '链接', '输入框', '下拉框', '日期', '勾选', '单选', '开关', '选项', '分页', '页签']);

const CANDIDATES = [
  'button', 'a[href]', 'select', 'summary', '[role=button]', '[role=link]', '[role=tab]', '[role=menuitem]',
  '[role=menuitemcheckbox]', '[role=menuitemradio]', '[role=checkbox]', '[role=radio]', '[role=switch]', '[role=option]',
  '[role=combobox]', '[role=treeitem]', '.el-button', '.el-link', '.el-tabs__item', '.el-menu-item', '.el-sub-menu__title',
  '.el-pager li', '.btn-prev', '.btn-next', '.el-select__wrapper', '.el-select', '.el-cascader', 'input', 'textarea',
  '.el-checkbox', '.el-radio', '.el-switch', '.el-tree-node__content', '.el-collapse-item__header', '.el-select-dropdown__item',
  '.el-dropdown-menu__item', '.el-cascader-node', '.el-dropdown', '[contenteditable=true]', '[onclick]', '[tabindex="0"]',
  '[draggable="true"]',
].join(',');

/** 根下所有元素，含开放的 Shadow DOM 里的。 */
function allIn(root: ParentNode): Element[] {
  const out: Element[] = [];
  const walk = (r: ParentNode) => {
    for (const el of Array.from(r.querySelectorAll('*'))) {
      out.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(root);
  return out;
}

function parentOf(el: Element): Element | null {
  const p = el.parentNode;
  return p instanceof ShadowRoot ? p.host : (p as Element | null);
}

/** 没有语义标记、只靠点击事件的元素：鼠标移上去变手形，且是手形区域的最外层。 */
function pointerStyled(el: Element, cursor: Map<Element, string>): boolean {
  const of = (e: Element) => {
    let c = cursor.get(e);
    if (c == null) {
      c = getComputedStyle(e).cursor;
      cursor.set(e, c);
    }
    return c;
  };
  if (of(el) !== 'pointer') return false;
  const p = parentOf(el);
  return !p || p === document.body || of(p) !== 'pointer';
}

function kindOf(el: Element): Kind | null {
  const c = el.classList;
  const role = el.getAttribute('role');
  // 能打字的 combobox（日期框、自动补全）按输入框处理。
  if (el.tagName === 'SELECT' || (role === 'combobox' && !el.matches('input, textarea') && !el.closest('.el-select, .el-cascader'))) return '下拉框';
  if (el.tagName === 'SUMMARY') return '折叠项';
  if (role === 'link') return '链接';
  if (role === 'treeitem') return '树节点';
  if (role === 'menuitemcheckbox' || role === 'menuitemradio') return '菜单';
  if (c.contains('el-select-dropdown__item') || c.contains('el-dropdown-menu__item') || c.contains('el-cascader-node') || role === 'option') return '选项';
  if (c.contains('el-select__wrapper') || c.contains('el-cascader')) return '下拉框';
  if (c.contains('el-select')) return el.querySelector('.el-select__wrapper') ? null : '下拉框';
  if (c.contains('el-checkbox') || role === 'checkbox') return '勾选';
  if (c.contains('el-radio') || role === 'radio') return '单选';
  if (c.contains('el-switch') || role === 'switch') return '开关';
  if (c.contains('el-tabs__item') || role === 'tab') return '页签';
  if (c.contains('el-menu-item') || c.contains('el-sub-menu__title') || role === 'menuitem') return '菜单';
  if (el.matches('.el-pager li, .btn-prev, .btn-next')) return '分页';
  if (c.contains('el-tree-node__content')) return '树节点';
  if (c.contains('el-collapse-item__header')) return '折叠项';
  if (el.matches('input, textarea, [contenteditable=true]')) {
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (el.closest('.el-select, .el-cascader, .el-checkbox, .el-radio, .el-switch')) return null;
    if (type === 'checkbox') return '勾选';
    if (type === 'radio') return '单选';
    if (['button', 'submit', 'reset', 'image'].includes(type)) return '按钮';
    if (['hidden', 'file', 'range', 'color'].includes(type)) return null;
    return el.closest('.el-date-editor') ? '日期' : '输入框';
  }
  if (el.matches('a[href], .el-link')) return '链接';
  if (el.matches('button, .el-button, [role=button], .el-dropdown')) return '按钮';
  if (el.matches('[draggable="true"]')) return '可拖';
  if (el.matches('[onclick], [tabindex="0"]')) return '可点';
  return null;
}

function disabled(el: Element) {
  return (
    (el as HTMLButtonElement).disabled === true ||
    el.getAttribute('aria-disabled') === 'true' ||
    /\bis-disabled\b/.test(el.className?.toString?.() || '') ||
    !!el.closest('.is-disabled, [disabled]')
  );
}

function fieldLabel(el: Element): string {
  const item = el.closest('.el-form-item');
  const label = item?.querySelector('.el-form-item__label') as HTMLElement | null;
  if (label) return squash(label.innerText).replace(/[:：]$/, '');
  const id = el.getAttribute('id');
  const forLabel = id ? (document.querySelector(`label[for="${CSS.escape(id)}"]`) as HTMLElement | null) : null;
  const wrap = el.closest('label') as HTMLElement | null;
  return squash(forLabel?.innerText || wrap?.innerText).replace(/[:：]$/, '');
}

function nameOf(el: Element, kind: Kind): string {
  const aria = el.getAttribute('aria-label') || el.getAttribute('title') || '';
  if (kind === '输入框' || kind === '日期' || kind === '下拉框') {
    const input = (el.matches('input, textarea') ? el : el.querySelector('input, textarea')) as HTMLInputElement | null;
    return clip(fieldLabel(el) || aria || input?.placeholder || '', 30);
  }
  const text = squash((el as HTMLElement).innerText);
  if (text) return clip(text, 40);
  if (aria) return clip(aria, 40);
  const label = fieldLabel(el);
  if (label) return clip(label, 40);
  const icon = el.querySelector('svg, i, .el-icon');
  const hint = squash(icon?.getAttribute('aria-label') || icon?.className?.toString?.().match(/(?:icon|el-icon)-([\w-]+)/)?.[1]);
  return hint ? `图标:${hint}` : '无文字图标';
}

function stateOf(el: Element, kind: Kind, name: string): string {
  if (kind === '输入框' || kind === '日期') {
    const input = (el.matches('input, textarea') ? el : el.querySelector('input, textarea')) as HTMLInputElement | null;
    const v = input ? input.value : squash((el as HTMLElement).innerText);
    const hidden = [name, input?.name, input?.placeholder].some((x) => PRIVATE_NAME.test(x || ''));
    const shown = hidden && v ? '(已隐藏)' : v ? `= ${clip(maskContacts(v), 60)}` : `(空${input?.placeholder ? `，提示：${clip(input.placeholder, 20)}` : ''})`;
    return shown;
  }
  if (kind === '下拉框' && el instanceof HTMLSelectElement) {
    const picked = Array.from(el.selectedOptions)
      .filter((o) => o.value !== '')
      .map((o) => squash(o.text))
      .filter(Boolean);
    return picked.length ? `= ${clip(picked.join('、'), 60)}` : '(未选)';
  }
  if (kind === '下拉框') {
    const empty = el.querySelector('.el-select__placeholder.is-transparent, .el-select__placeholder:only-child');
    const tags = Array.from(el.querySelectorAll('.el-tag, .el-select__selected-item:not(.el-select__placeholder)'))
      .map((t) => squash((t as HTMLElement).innerText))
      .filter(Boolean);
    const text = tags.length ? tags.join('、') : squash((el.querySelector('.el-select__selected-item, .el-input__inner') as HTMLInputElement | null)?.innerText || (el.querySelector('input') as HTMLInputElement | null)?.value);
    return empty || !text ? '(未选)' : `= ${clip(maskContacts(text), 60)}`;
  }
  if (kind === '勾选' || kind === '单选' || kind === '开关') {
    const input = (el instanceof HTMLInputElement ? el : el.querySelector('input')) as HTMLInputElement | null;
    const on = el.classList.contains('is-checked') || el.getAttribute('aria-checked') === 'true' || input?.checked;
    return on ? '(已选)' : '(未选)';
  }
  if (kind === '页签' || kind === '菜单' || kind === '分页' || kind === '选项') {
    return el.matches('.is-active, .is-selected, [aria-selected=true]') ? '(当前)' : '';
  }
  return '';
}

function rowContext(el: Element): string {
  const tr = el.closest('tr');
  if (!tr || !tr.closest('tbody')) return '';
  const rows = Array.from(tr.parentElement?.children || []).filter((r) => r.tagName === 'TR');
  const first = Array.from(tr.querySelectorAll('td'))
    .map((td) => squash((td as HTMLElement).innerText))
    .find((t) => t && !/^\d{1,3}$/.test(t));
  return `第${rows.indexOf(tr) + 1}行${first ? `：${clip(maskContacts(first), 24)}` : ''}`;
}

function offscreen(el: Element) {
  const r = el.getBoundingClientRect();
  return r.bottom < 0 || r.top > window.innerHeight || r.right < 0 || r.left > window.innerWidth;
}

type Item = { el: Element; kind: Kind; line: string };

function collect(root: ParentNode, keyword: string): Item[] {
  const out: Item[] = [];
  const taken = new Set<Element>();
  const cursor = new Map<Element, string>();
  const insideTaken = (el: Element) => {
    for (let p = parentOf(el); p && p !== root; p = parentOf(p)) if (taken.has(p)) return true;
    return false;
  };
  for (const el of allIn(root)) {
    if (ownUi(el) || insideTaken(el)) continue;
    const kind = el.matches(CANDIDATES) ? kindOf(el) : pointerStyled(el, cursor) ? '可点' : null;
    if (!kind || !visible(el) || isSecretInput(el)) continue;
    if (kind === '可点') {
      const text = squash((el as HTMLElement).innerText);
      if (!text && !el.getAttribute('aria-label') && !el.getAttribute('title')) continue;
      // 只是给里面的按钮套了一层手形，按钮自己会列出来。
      const inner = el.querySelector(CANDIDATES) as HTMLElement | null;
      if (inner && squash(inner.innerText) === text) continue;
    }
    const name = nameOf(el, kind);
    const state = stateOf(el, kind, name);
    const row = rowContext(el);
    const flags = [disabled(el) ? '不可用' : '', offscreen(el) ? '屏幕外' : ''].filter(Boolean).join('，');
    // 鼠标移上去才显示的提示常写着隐藏用法（如“右键清空筛选”），文字里没有时带上。
    const tip = squash(el.getAttribute('title'));
    const tipPart = tip && !name.includes(tip) ? ` 提示「${clip(tip, 30)}」` : '';
    const line = `${refFor(el)} ${kind}「${name}」${state ? ` ${state}` : ''}${tipPart}${row ? `（${row}）` : ''}${flags ? ` [${flags}]` : ''}`;
    if (LEAF.has(kind)) taken.add(el);
    if (keyword && !line.includes(keyword)) continue;
    out.push({ el, kind, line });
  }
  return out;
}

const PICTURE = '[_echarts_instance_], canvas, img, svg';
const PICTURE_MAX = 8;

/** 图表和图片：文字读不到，列出来让模型知道有东西可以 look_at。 */
function pictures(root: ParentNode): Element[] {
  const out: Element[] = [];
  for (const el of Array.from(root.querySelectorAll(PICTURE))) {
    if (out.length >= PICTURE_MAX || !visible(el) || out.some((o) => o.contains(el))) continue;
    const r = el.getBoundingClientRect();
    if (r.width >= 120 && r.height >= 80) out.push(el);
  }
  return out;
}

function pictureName(el: Element): string {
  const own = el.getAttribute('alt') || el.getAttribute('aria-label') || el.getAttribute('title');
  const head = el.closest('.el-card')?.querySelector('.el-card__header') as HTMLElement | null;
  return clip(squash(own || head?.innerText) || '无标题', 30);
}

/** 当前挡在页面最上层的弹窗或抽屉（有遮罩的那种）。 */
const MODAL = 'dialog[open], [role=dialog][aria-modal="true"], [role=alertdialog]';
const OPTION = '.el-select-dropdown__item, .el-dropdown-menu__item, .el-cascader-node, [role=option], [role=menuitem]';

function topModal(): HTMLElement | null {
  const ep = Array.from(document.querySelectorAll('.el-overlay, .el-message-box__wrapper')).filter(
    (o) => visible(o) && o.querySelector('.el-dialog, .el-drawer, .el-message-box'),
  );
  const generic = Array.from(document.querySelectorAll(MODAL)).filter((o) => visible(o) && !o.closest('.el-overlay, .el-message-box__wrapper'));
  const z = (el: Element) => Number(getComputedStyle(el).zIndex) || 0;
  // 同层级时后出现的在上面。
  const layers = [...ep, ...generic] as HTMLElement[];
  return layers.reduce<HTMLElement | null>((top, el) => (!top || z(el) >= z(top) ? el : top), null);
}

function openPoppers(): HTMLElement[] {
  const ep = Array.from(document.querySelectorAll('.el-popper, .el-picker__popper, .el-select__popper'));
  const generic = Array.from(document.querySelectorAll('[role=listbox], [role=menu]')).filter((l) => !l.closest('.el-popper'));
  return ([...ep, ...generic] as HTMLElement[]).filter((p) => visible(p) && p.querySelector(OPTION));
}

function titleOf(layer: Element): string {
  const by = layer.getAttribute('aria-labelledby');
  const t = ((by && document.getElementById(by)) ||
    layer.querySelector('.el-dialog__title, .el-drawer__title, .el-message-box__title, header, [role=heading], h1, h2, h3')) as HTMLElement | null;
  return clip(squash(t?.innerText || layer.getAttribute('aria-label')), 30);
}

function toasts(): string[] {
  return (Array.from(document.querySelectorAll('.el-message, .el-notification, [role=alert], [role=status]')) as HTMLElement[])
    .filter(visible)
    .map((t) => clip(maskContacts(squash(t.innerText)), 80))
    .filter(Boolean);
}

function mainRoot(): HTMLElement {
  return (document.querySelector('.vben-layout-content, main, [role=main]') as HTMLElement | null) ?? document.body;
}

/** 弹窗层里真正的对话框（Element Plus 的遮罩层比对话框大）。 */
function modalBox(layer: HTMLElement): HTMLElement {
  return (layer.querySelector('.el-dialog, .el-drawer, .el-message-box') as HTMLElement | null) ?? layer;
}

/** 页面的文字版：最上层优先（弹窗、展开的下拉），每个可操作元素一行，前面是编号。 */
export function readPage(opts: { keyword?: string; text?: boolean; limit?: number } = {}): string {
  pruneRefs();
  const keyword = squash(opts.keyword);
  const limit = opts.limit ?? MAX_LINES;
  const lines: string[] = [`页面：${location.pathname}${location.search} 「${clip(squash(document.title), 40)}」`];
  const modal = topModal();
  let budget = limit;
  let found = 0;
  const add = (head: string, items: Item[]) => {
    found += items.length;
    if (!items.length || budget <= 0) return;
    lines.push(head, ...items.slice(0, budget).map((i) => `  ${i.line}`));
    if (items.length > budget) lines.push(`  …还有 ${items.length - budget} 个没列出，用 keyword 缩小范围`);
    budget -= items.length;
  };
  for (const p of openPoppers()) add('展开的选项：', collect(p, keyword));
  const pics = pictures(modal ?? mainRoot())
    .map((el) => {
      const r = el.getBoundingClientRect();
      return `  ${refFor(el)} 图「${pictureName(el)}」 ${Math.round(r.width)}×${Math.round(r.height)}${offscreen(el) ? ' [屏幕外]' : ''}`;
    })
    .filter((line) => !keyword || line.includes(keyword));
  found += pics.length;
  if (modal) {
    add(`弹窗「${titleOf(modal)}」（挡在页面上面，下面的页面要等它关掉才能点）：`, collect(modal, keyword));
  } else {
    const root = mainRoot();
    const side = Array.from(document.querySelectorAll('.vben-layout-sidebar, aside, .el-menu, nav')).find((s) => !root.contains(s) && visible(s));
    add('页面：', collect(root, keyword));
    if (side && keyword) add('侧边菜单：', collect(side, keyword));
    else if (side) {
      const n = collect(side, '').length;
      if (n) lines.push(`侧边菜单 ${n} 项没列出（要去别的页面，用 keyword 找到菜单再点）`);
    }
    const tables = readPageTables().slice(0, 3);
    for (const t of tables) {
      lines.push(`表格「${t.title}」本页 ${t.rows.length} 行${t.total != null ? `，共 ${t.total} 条` : ''}；列：${t.columns.slice(0, 20).join('、')}`);
    }
  }
  if (pics.length) lines.push('图表和图片（内容是画出来的，文字读不到，要看用 look_at）：', ...pics);
  const msgs = toasts();
  if (msgs.length) lines.push(`提示消息：${msgs.join(' / ')}`);
  // 关键词没命中时直接给整页清单，模型不用再读一次。
  if (keyword && !found) return `没有含「${keyword}」的元素，下面是不带 keyword 的整页清单：\n${readPage({ ...opts, keyword: '' })}`;
  if (opts.text) {
    const body = (modal ?? mainRoot()).innerText || '';
    lines.push(`正文：${clip(maskContacts(squash(body)), 4000)}`);
  }
  if (lines.length === 1) lines.push('没有找到可操作元素（页面可能还在加载）');
  return lines.join('\n');
}

/** 每轮第一步随请求带上的页面清单，模型不用先花一步 read_page。 */
export const pageListing = () => readPage({ limit: AFTER_ACTION_LINES });

// ---------------------------------------------------------------- 操作

let lastTrigger = '';
let guardTimer: number | undefined;
type WriteRecord = { request: string; decision: '等用户决定' | '用户放行' | '按「本轮都放行」放行' | '用户拦下'; status?: number; response?: string };
const writesThisAction: WriteRecord[] = [];
/** 用户在卡片上点了「本轮都放行」：这一轮余下的提交不再逐个确认。 */
let allowRest = false;
let turnSignal: AbortSignal | null = null;
let progress: ((text: string) => void) | null = null;
let onTakeover: (() => void) | null = null;
let actedThisTurn = false;
/** 第几轮。被停下的旧一轮可能还卡在等页面安静，它醒来时不能动新一轮的状态，也不能再动页面。 */
let turnNo = 0;
/** 宠物最近一次动页面的时间；在这之前的用户操作不能让宠物触发的提交免确认。 */
let armedAt = 0;

/** 每轮开始时调用：撤销上一轮的「本轮都放行」，登记停止信号、进度回调和用户接手时的回调。返回这一轮的编号。 */
export function beginTurn(signal: AbortSignal | null, onProgress: ((text: string) => void) | null, takeover: (() => void) | null = null): number {
  turnNo += 1;
  allowRest = false;
  turnSignal = signal;
  progress = onProgress;
  onTakeover = takeover;
  actedThisTurn = false;
  return turnNo;
}

export const currentTurn = () => turnNo;

/** 这一轮结束：之后用户再点页面不算接手。提交确认的尾巴照常走完（中途出错退出的操作没走到 after，从这里起算）。新一轮已经开始时什么都不动。 */
export function endTurn(turn = turnNo) {
  if (turn !== turnNo) return;
  restartTail();
  pointer?.end(!!turnSignal?.aborted);
  turnSignal = null;
  progress = null;
  onTakeover = null;
  actedThisTurn = false;
}

/** 用户停了、接手了，或已经开始了新一轮：在真正动页面之前退出，指针收起。turn 是这个操作开始时的轮次。 */
function stopIfAborted(turn: number) {
  if (turn === turnNo && !turnSignal?.aborted) return;
  if (turn === turnNo) pointer?.done();
  throw new DOMException('Aborted', 'AbortError');
}

/** 「本轮都放行」只管卡片所属的那一轮；前几轮留下的卡片点了只放行它自己。 */
export function allowRestOfTurn(turn = turnNo) {
  if (turn === turnNo) allowRest = true;
}

/** 操作期间和之后 GUARD_TAIL_MS 内，页面发出的非查询请求先暂停，交给用户决定。 */
function armGuard(trigger: string) {
  lastTrigger = trigger;
  actedThisTurn = true;
  armedAt = Date.now();
  window.clearTimeout(guardTimer);
  setWriteHold(async (req) => {
    if (humanAt > armedAt && Date.now() - humanAt < HUMAN_WRITE_MS) return true;
    const path = (() => {
      try {
        const url = new URL(req.url, location.href);
        return url.origin === location.origin ? url.pathname : `${url.host}${url.pathname}`;
      } catch {
        return req.url;
      }
    })();
    const kind = writeKind(req.method, path);
    const rec: WriteRecord = { request: `${req.method} ${path}`, decision: '等用户决定' };
    writesThisAction.push(rec);
    let report: (r: WriteResult) => void = () => {};
    const result = new Promise<WriteResult>((r) => (report = r));
    req.onResult = (status, text) => {
      rec.status = status;
      rec.response = clip(maskContacts(squash(text)), 200);
      report({ status, text: rec.response });
    };
    if (!onHeldWrite) {
      rec.decision = '用户拦下';
      return false;
    }
    // 删除收不回来，「本轮都放行」也逐个问。
    const auto = allowRest && kind !== '删除';
    if (!auto) progress?.('等你在卡片上决定要不要提交…');
    const ok = await onHeldWrite({ method: req.method, path, kind, body: clip(maskContacts(bodyText(req.body)), 300), trigger: lastTrigger, auto, result, turn: turnNo });
    rec.decision = !ok ? '用户拦下' : auto || allowRest ? '按「本轮都放行」放行' : '用户放行';
    return ok;
  });
}

/** 尾巴从操作真正做完时算起：远程搜索的下拉可能等上十几秒才点到选项。 */
function restartTail() {
  window.clearTimeout(guardTimer);
  guardTimer = window.setTimeout(() => setWriteHold(null), GUARD_TAIL_MS);
}

/** 立刻不再暂停页面的请求，撤销「本轮都放行」。尾巴到时只撤暂停：模型想下一步常要十几秒，「本轮都放行」要管到这一轮结束。 */
export function stopGuard() {
  window.clearTimeout(guardTimer);
  setWriteHold(null);
  allowRest = false;
}

/** 用户点了停止：撤销「本轮都放行」。确认继续开到尾巴结束，宠物已经触发、晚发出的提交（防抖自动保存）照样要问；用户自己的提交不受影响。 */
export function revokeAllowRest() {
  allowRest = false;
}

const DELETE_WORDS = new Set(['delete', 'del', 'remove', 'destroy', 'drop']);
const CREATE_WORDS = new Set(['create', 'add', 'insert', 'new', 'save']);

/** 给用户看的提交类型，按方法和路径词猜，猜不出就叫「提交」。 */
export function writeKind(method: string, path: string): string {
  const m = method.toUpperCase();
  const words = path.split(/[/_\-.]+|(?=[A-Z])/).map((w) => w.toLowerCase());
  if (m === 'DELETE' || words.some((w) => DELETE_WORDS.has(w))) return '删除';
  if (m === 'PUT' || m === 'PATCH') return '修改';
  if (words.some((w) => CREATE_WORDS.has(w))) return '新建或保存';
  return '提交';
}

function bodyText(body: unknown): string {
  if (body == null) return '';
  if (typeof body === 'string') return body;
  if (body instanceof URLSearchParams) return body.toString();
  if (body instanceof FormData) return [...body.keys()].map((k) => `${k}=…`).join('&');
  return '';
}

/** 等页面安静下来：页面发出的请求都回来了、且一段时间没有 DOM 变化，或到上限。 */
function settle(): Promise<void> {
  return new Promise((done) => {
    let quiet = window.setTimeout(check, SETTLE_QUIET_MS);
    const cap = window.setTimeout(finish, SETTLE_MAX_MS);
    const mo = new MutationObserver(() => {
      window.clearTimeout(quiet);
      quiet = window.setTimeout(check, SETTLE_QUIET_MS);
    });
    mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
    function check() {
      if (pendingRequests() > 0) quiet = window.setTimeout(check, 150);
      else finish();
    }
    function finish() {
      mo.disconnect();
      window.clearTimeout(quiet);
      window.clearTimeout(cap);
      done();
    }
  });
}

function describe(el: Element): string {
  if (!kindOf(el) && el.matches(PICTURE)) return `图「${pictureName(el)}」`;
  const kind = kindOf(el) ?? '按钮';
  return `${kind}「${nameOf(el, kind)}」`;
}

/** 改之前的值，写进结果和操作记录，用户说“改回去”时有据可依。 */
function previousValue(el: Element): string {
  const kind = kindOf(el);
  const state = kind ? stateOf(el, kind, nameOf(el, kind)) : '';
  return state ? `（原来 ${state}）` : '';
}

const unsettled = (w: WriteRecord) => w.decision === '等用户决定' || (w.decision !== '用户拦下' && w.status == null);

/** 有提交被暂停时，等用户决定、等放行的请求返回（最多 HELD_WAIT_MS），这样下一步能按真实结果走。 */
async function waitForWrites(writes: WriteRecord[], turn: number) {
  const until = Date.now() + HELD_WAIT_MS;
  while (writes.some(unsettled) && Date.now() < until && turn === turnNo && !turnSignal?.aborted) {
    await new Promise((r) => window.setTimeout(r, 200));
  }
}

function writesNote(writes: WriteRecord[]): string {
  if (writes.some((w) => w.decision === '等用户决定')) {
    return '有提交还在等用户在卡片上点「放行」或「拦下」；回答里如实说在等确认，不要说已经保存或已经提交';
  }
  if (writes.some((w) => w.status != null)) {
    return '放行的提交已经发出，成功与否看 status 和 response（很多系统 200 里也会带错误码和提示），不要只凭点了按钮就说成功';
  }
  return writes.some((w) => w.decision === '用户拦下') ? '用户拦下了提交，这次没有写进系统' : '';
}

/** 操作后的结果：页面有没有跳转、弹出了什么、提示了什么、提交的去向和系统的回复，再附上新的页面清单。 */
async function after(done: string, beforePath: string): Promise<string> {
  const turn = turnNo;
  restartTail();
  await settle();
  const writes = writesThisAction.splice(0);
  if (writes.some(unsettled)) {
    await waitForWrites(writes, turn);
    await settle();
    writes.push(...writesThisAction.splice(0));
  }
  const now = location.pathname + location.search;
  return JSON.stringify({
    done,
    ...(now !== beforePath ? { page_changed_to: now } : {}),
    ...(writes.length ? { held_writes: writes, note: writesNote(writes) } : {}),
    toasts: toasts(),
    page: readPage({ limit: AFTER_ACTION_LINES }),
  });
}

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

/** 元素中心在屏幕内，也没被外层滚动容器裁掉。 */
function inView(el: Element): boolean {
  const { x, y } = center(el);
  if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) return false;
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    if (!/(auto|scroll|hidden|clip)/.test(getComputedStyle(p).overflow)) continue;
    const c = p.getBoundingClientRect();
    if (x < c.left || x > c.right || y < c.top || y > c.bottom) return false;
  }
  return true;
}

/** 等平滑滚动停下：连续两次位置不变，最多等 900ms。 */
async function settleScroll(el: Element) {
  let last = '';
  for (let i = 0, still = 0; i < 18 && still < 2; i += 1) {
    await new Promise((r) => window.setTimeout(r, 50));
    const r = el.getBoundingClientRect();
    const now = `${Math.round(r.left)},${Math.round(r.top)}`;
    still = now === last ? still + 1 : 0;
    last = now;
  }
}

/** 像用户一样把元素滚进视野：已经看得见就不动页面，要滚就平滑地滚。 */
async function bringIntoView(el: Element, force = false) {
  if (!force && inView(el)) return;
  (el as HTMLElement).scrollIntoView?.({ block: 'center', inline: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' });
  await settleScroll(el);
}

/**
 * 别的控件展开的下拉、菜单、日期面板挡在目标上时，先像用户一样点一下空白处收起它。
 * 不按 Esc：弹窗里的下拉被 Esc 收起时，弹窗自己也可能跟着关掉。
 */
async function clearCover(el: Element) {
  const { x, y } = center(el);
  const hit = deepestAt(x, y);
  if (!hit || el.contains(hit) || hit.contains(el) || ownUi(hit)) return;
  const pop = hit.closest('.el-popper, .el-picker__popper, [role=listbox], [role=menu], [role=tooltip]');
  if (!pop || pop.contains(el)) return;
  const corner = { x: 1, y: 1 };
  for (const [type, C] of [['pointerdown', P], ['mousedown', MouseEvent], ['pointerup', P], ['mouseup', MouseEvent], ['click', MouseEvent]] as const) {
    fire(document.body, type, C, corner);
  }
  await settle();
}

/** 弹窗挡在页面上时，用户点不到弹窗外面的东西（从弹窗里展开、挂在页面最外层的下拉面板除外）。 */
function underModal(el: Element): string {
  const modal = topModal();
  if (!modal || modal.contains(el) || el.closest('.el-popper, .el-picker__popper')) return '';
  return titleOf(modal);
}

/**
 * 指针飞过去；返回空串表示可以动手，否则是给模型的错误：落下时元素已经被页面换掉，
 * 或被弹窗挡住（用户自己也点不到）。
 */
async function pointAt(el: Element, label: string, kind: PointerKind): Promise<string> {
  const turn = turnNo;
  await bringIntoView(el);
  stopIfAborted(turn);
  if (kind !== 'point' && kind !== 'look') {
    await clearCover(el);
    const modal = underModal(el);
    if (modal) return JSON.stringify({ error: `${label} 被弹窗「${modal}」挡住了，用户也点不到；先处理弹窗，或 read_page 看弹窗里的编号` });
  }
  await pointer?.show(el, label, kind);
  stopIfAborted(turn);
  if (el.isConnected) return '';
  pointer?.done();
  return goneMidway(label);
}

const goneMidway = (label: string) => JSON.stringify({ error: `${label} 在操作前被页面换掉了（刚刷新或重新渲染），先 read_page 拿新编号` });

const P = typeof PointerEvent === 'function' ? PointerEvent : MouseEvent;
const center = (el: Element) => {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
};

function fire(el: Element, type: string, Ctor: typeof MouseEvent | typeof PointerEvent = MouseEvent, at = center(el), button = 0, detail = 1) {
  // enter / leave 在真实浏览器里不冒泡。
  const bubbles = !/(enter|leave)$/.test(type);
  const buttons = /down|move/.test(type) ? (button === 2 ? 2 : 1) : 0;
  const init = { bubbles, cancelable: true, composed: true, clientX: at.x, clientY: at.y, button, buttons, detail, view: window };
  el.dispatchEvent(new Ctor(type, init));
}

/** 坐标处最里层的元素，穿进开放的 Shadow DOM。 */
function deepestAt(x: number, y: number): Element | null {
  let el = document.elementFromPoint(x, y);
  while (el?.shadowRoot) {
    const inner = el.shadowRoot.elementFromPoint(x, y);
    if (!inner || inner === el) break;
    el = inner;
  }
  return el;
}

/** 真实鼠标移进来时，从外到里每一层都收到 enter，最里层收到 over / move；只发给外层的话，挂在里层的悬停监听收不到。 */
function hoverOn(el: Element) {
  const at = center(el);
  const inner = deepestAt(at.x, at.y);
  const chain: Element[] = [];
  for (let e: Element | null = inner; e; e = parentOf(e)) {
    chain.unshift(e);
    if (e === el) break;
  }
  // 坐标处是别的元素（被遮住或不在这里）时，只发给目标自己。
  if (chain[0] !== el) chain.splice(0, chain.length, el);
  for (const e of chain) {
    fire(e, 'pointerenter', P, at);
    fire(e, 'mouseenter', MouseEvent, at);
  }
  const target = chain[chain.length - 1]!;
  for (const [type, C] of [['pointerover', P], ['mouseover', MouseEvent], ['pointermove', P], ['mousemove', MouseEvent]] as const) {
    fire(target, type, C, at);
  }
}

function pressOn(el: Element) {
  hoverOn(el);
  fire(el, 'pointerdown', P);
  fire(el, 'mousedown');
  (el as HTMLElement).focus?.({ preventScroll: true });
  fire(el, 'pointerup', P);
  fire(el, 'mouseup');
  (el as HTMLElement).click();
}

/** 右键：只发按下、松开和 contextmenu，不发 click。 */
function rightClickOn(el: Element) {
  hoverOn(el);
  fire(el, 'pointerdown', P, center(el), 2);
  fire(el, 'mousedown', MouseEvent, center(el), 2);
  fire(el, 'pointerup', P, center(el), 2);
  fire(el, 'mouseup', MouseEvent, center(el), 2);
  fire(el, 'contextmenu', MouseEvent, center(el), 2);
}

const MAX_REPEAT = 20;

export async function clickRef(ref: string, opts: { right?: boolean; double?: boolean; times?: number } = {}): Promise<string> {
  const el = resolve(ref);
  if (typeof el === 'string') return JSON.stringify({ error: el });
  if (disabled(el)) return JSON.stringify({ error: `${describe(el)} 现在不可用（灰的），可能要先满足别的条件` });
  const how = opts.right ? '右键' : opts.double ? '双击' : '';
  const times = how ? 1 : Math.min(MAX_REPEAT, Math.max(1, Math.floor(Number(opts.times) || 1)));
  const label = describe(el);
  const before = location.pathname + location.search;
  const turn = turnNo;
  armGuard(`${how || '点'}了${label}`);
  let clicked = 0;
  let cut = '';
  while (clicked < times) {
    if (clicked) {
      // 每次点完等页面跟上（加出来的行渲染好）再点下一次；中途要提交、元素没了或变灰就停，按实际次数报告。
      if (!writesThisAction.length) await settle();
      stopIfAborted(turn);
      if (writesThisAction.length) cut = '页面要提交数据';
      else if (!el.isConnected) cut = '元素已经不在页面上';
      else if (disabled(el)) cut = '元素变成不可用';
      if (cut) break;
    }
    const miss = await pointAt(el, `${how}${label}${times > 1 ? `（${clicked + 1}/${times}）` : ''}`, 'click');
    if (miss) {
      if (!clicked) return miss;
      cut = '元素被挡住或被页面换掉';
      break;
    }
    try {
      if (opts.right) rightClickOn(el);
      else {
        pressOn(el);
        if (opts.double) {
          pressOn(el);
          fire(el, 'dblclick', MouseEvent, center(el), 0, 2);
        }
      }
    } finally {
      pointer?.done();
    }
    clicked += 1;
  }
  const count = times > 1 ? `，共点了 ${clicked} 次${cut ? `（要点 ${times} 次，${cut}，没点满）` : ''}` : '';
  return after(`${how || '点击'}了 ${ref} ${label}${count}`, before);
}

function setNativeValue(input: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value')?.set?.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * 工具里的键名 → [KeyboardEvent.key, code, keyCode]。脚本派发的按键只有页面自己的键盘处理收得到，
 * 浏览器不会执行默认动作（删字、翻页、移光标），所以只留页面会处理的键；Tab 由 pressKey 自己挪焦点。
 */
const KEYS: Record<string, [string, string, number]> = {
  Enter: ['Enter', 'Enter', 13],
  Escape: ['Escape', 'Escape', 27],
  Tab: ['Tab', 'Tab', 9],
  Space: [' ', 'Space', 32],
  ArrowUp: ['ArrowUp', 'ArrowUp', 38],
  ArrowDown: ['ArrowDown', 'ArrowDown', 40],
  ArrowLeft: ['ArrowLeft', 'ArrowLeft', 37],
  ArrowRight: ['ArrowRight', 'ArrowRight', 39],
};

const TABBABLE = 'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]';

/** 浏览器不会为脚本按的 Tab 挪焦点，这里按文档顺序挪到下一个能聚焦的元素。 */
function focusNext(from: Element | null) {
  const all = (Array.from(document.querySelectorAll(TABBABLE)) as HTMLElement[]).filter(
    (el) => el.tabIndex >= 0 && !disabled(el) && visible(el) && !ownUi(el),
  );
  const at = from ? all.findIndex((el) => el === from || el.contains(from)) : -1;
  all[at + 1]?.focus();
}

function key(el: Element, name: string) {
  const [k, code, keyCode] = KEYS[name] ?? [name, name, 0];
  for (const type of ['keydown', 'keypress', 'keyup']) {
    el.dispatchEvent(new KeyboardEvent(type, { key: k, code, keyCode, which: keyCode, bubbles: true, cancelable: true } as any));
  }
}

export async function typeRef(ref: string, text: string, opts: { append?: boolean; enter?: boolean } = {}): Promise<string> {
  const el = resolve(ref);
  if (typeof el === 'string') return JSON.stringify({ error: el });
  if (isSecretInput(el)) return JSON.stringify({ error: '密码类输入框不能代填，请用户自己输入' });
  const input = (el.matches('input, textarea') ? el : el.querySelector('input, textarea')) as HTMLInputElement | HTMLTextAreaElement | null;
  const editable = !input && el.getAttribute('contenteditable') === 'true' ? (el as HTMLElement) : null;
  if (!input && !editable) return JSON.stringify({ error: `${describe(el)} 不是输入框，先 read_page 找输入框的编号` });
  if (input && (input.readOnly || input.disabled)) {
    return JSON.stringify({ error: `${describe(el)} 是只读的（多半是下拉或日期选择），用 choose_option 或点开它选` });
  }
  const label = describe(el);
  const was = previousValue(el);
  const before = location.pathname + location.search;
  armGuard(`在${label}里输入`);
  const miss = await pointAt(el, label, 'type');
  if (miss) return miss;
  try {
    const target = (input ?? editable)!;
    target.focus();
    if (input) {
      setNativeValue(input, opts.append ? input.value + text : text);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      editable!.innerText = opts.append ? editable!.innerText + text : text;
      editable!.dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (opts.enter) key(target, 'Enter');
  } finally {
    pointer?.done();
  }
  return after(`在 ${ref} ${label} 输入了「${clip(text, 40)}」${opts.enter ? '并回车' : ''}${was}`, before);
}

function optionsIn(poppers: HTMLElement[]): HTMLElement[] {
  return poppers.flatMap((p) =>
    (Array.from(p.querySelectorAll(OPTION)) as HTMLElement[]).filter((o) => visible(o) && !disabled(o)),
  );
}

/** 打开下拉框，选文字对得上的选项；可搜索的下拉先输入关键词。 */
export async function chooseRef(ref: string, option: string): Promise<string> {
  const el = resolve(ref);
  if (typeof el === 'string') return JSON.stringify({ error: el });
  const want = squash(option);
  const label = describe(el);
  const was = previousValue(el);
  const before = location.pathname + location.search;
  armGuard(`在${label}里选「${want}」`);
  const turn = turnNo;
  const miss = await pointAt(el, label, 'click');
  if (miss) return miss;
  if (el instanceof HTMLSelectElement) {
    try {
      const all = Array.from(el.options).filter((o) => !o.disabled);
      const pick = all.find((o) => squash(o.text) === want) ?? all.find((o) => squash(o.text).includes(want));
      if (!pick) return JSON.stringify({ error: `「${want}」不在 ${label} 的选项里`, options: all.map((o) => clip(squash(o.text), 30)).slice(0, 40) });
      el.focus();
      if (el.multiple) pick.selected = true;
      else Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')?.set?.call(el, pick.value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } finally {
      pointer?.done();
    }
    return after(`在 ${ref} ${label} 选了「${want}」${was}`, before);
  }
  try {
    pressOn(el);
    await settle();
    stopIfAborted(turn);
    let opts = optionsIn(openPoppers());
    const search = el.querySelector('input:not([readonly])') as HTMLInputElement | null;
    if (search && !opts.some((o) => squash(o.innerText) === want)) {
      search.focus();
      setNativeValue(search, want);
      await settle();
      stopIfAborted(turn);
      opts = optionsIn(openPoppers());
    }
    const pick = opts.find((o) => squash(o.innerText) === want) ?? opts.find((o) => squash(o.innerText).includes(want));
    if (!pick) {
      const seen = opts.map((o) => clip(squash(o.innerText), 30)).filter(Boolean).slice(0, 40);
      key(document.activeElement ?? document.body, 'Escape');
      return JSON.stringify({ error: `「${want}」不在 ${label} 的选项里`, options: seen });
    }
    await pointer?.show(pick, `选项「${clip(squash(pick.innerText), 30)}」`, 'click');
    stopIfAborted(turn);
    pressOn(pick);
  } finally {
    pointer?.done();
  }
  return after(`在 ${ref} ${label} 选了「${want}」${was}`, before);
}

export async function scrollPage(opts: { ref?: string; direction?: 'up' | 'down' }): Promise<string> {
  const before = location.pathname + location.search;
  if (opts.ref) {
    const el = resolve(opts.ref);
    if (typeof el === 'string') return JSON.stringify({ error: el });
    await bringIntoView(el, true);
    return after(`滚动到 ${opts.ref}`, before);
  }
  const modal = topModal();
  const root = modal ? (modal.querySelector('.el-dialog__body, .el-drawer__body') ?? scrollable(modalBox(modal))) : scrollable(mainRoot());
  const dy = (opts.direction === 'up' ? -1 : 1) * Math.round(window.innerHeight * 0.8);
  root.scrollBy({ top: dy, behavior: reducedMotion() ? 'auto' : 'smooth' });
  await settleScroll(root === document.scrollingElement ? document.body : root.firstElementChild ?? root);
  return after(`向${opts.direction === 'up' ? '上' : '下'}滚了一屏`, before);
}

function scrollable(start: HTMLElement): Element {
  for (let el: HTMLElement | null = start; el; el = el.parentElement) {
    const st = getComputedStyle(el);
    if (/(auto|scroll)/.test(st.overflowY) && el.scrollHeight > el.clientHeight + 4) return el;
  }
  return document.scrollingElement ?? document.documentElement;
}

export async function pressKey(k: string): Promise<string> {
  if (!KEYS[k]) return JSON.stringify({ error: `只支持 ${Object.keys(KEYS).join(' / ')}` });
  const before = location.pathname + location.search;
  armGuard(`按了 ${k}`);
  const at = document.activeElement ?? document.body;
  key(at, k);
  if (k === 'Tab') focusNext(at === document.body ? null : at);
  return after(`按了 ${k}`, before);
}

/** 鼠标移上去不点：悬停菜单、提示气泡、悬停才出现的按钮。 */
export async function hoverRef(ref: string): Promise<string> {
  const el = resolve(ref);
  if (typeof el === 'string') return JSON.stringify({ error: el });
  const label = describe(el);
  const before = location.pathname + location.search;
  armGuard(`把鼠标移到${label}上`);
  const miss = await pointAt(el, label, 'hover');
  if (miss) return miss;
  try {
    hoverOn(el);
  } finally {
    pointer?.done();
  }
  return after(`鼠标移到了 ${ref} ${label} 上`, before);
}

/** 按住拖到另一个元素上：同时发指针 / 鼠标事件和 HTML5 拖放事件，两类拖拽实现都能收到。 */
export async function dragRef(ref: string, toRef: string): Promise<string> {
  const from = resolve(ref);
  if (typeof from === 'string') return JSON.stringify({ error: from });
  const to = resolve(toRef);
  if (typeof to === 'string') return JSON.stringify({ error: to });
  const label = `${describe(from)} 到 ${describe(to)}`;
  const before = location.pathname + location.search;
  armGuard(`把${label}`);
  const miss = (await pointAt(from, describe(from), 'drag')) || (to.isConnected ? '' : goneMidway(label));
  if (miss) {
    pointer?.done();
    return miss;
  }
  try {
    const a = center(from);
    const b = center(to);
    hoverOn(from);
    fire(from, 'pointerdown', P, a);
    fire(from, 'mousedown', MouseEvent, a);
    const dt = new DataTransfer();
    from.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, clientX: a.x, clientY: a.y, dataTransfer: dt }));
    await pointer?.show(to, describe(to), 'drag');
    for (let i = 1; i <= 8; i += 1) {
      const at = { x: a.x + ((b.x - a.x) * i) / 8, y: a.y + ((b.y - a.y) * i) / 8 };
      const over = document.elementFromPoint(at.x, at.y) ?? to;
      fire(over, 'pointermove', P, at);
      fire(over, 'mousemove', MouseEvent, at);
    }
    for (const type of ['dragenter', 'dragover', 'drop']) {
      to.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, clientX: b.x, clientY: b.y, dataTransfer: dt }));
    }
    fire(to, 'pointerup', P, b);
    fire(to, 'mouseup', MouseEvent, b);
    from.dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, clientX: b.x, clientY: b.y, dataTransfer: dt }));
  } finally {
    pointer?.done();
  }
  return after(`拖动了 ${label}`, before);
}

/** 编号对应元素的简短说明，进度提示用；失效时返回空串。 */
export function labelOf(ref: string): string {
  const el = byRef.get(String(ref || '').trim())?.deref();
  return el?.isConnected ? describe(el) : '';
}

/** 只把元素指给用户看，不操作。 */
export async function pointRef(ref: string, note: string): Promise<string> {
  const el = resolve(ref);
  if (typeof el === 'string') return JSON.stringify({ error: el });
  const label = describe(el);
  await pointAt(el, note ? clip(note, 30) : label, 'point');
  pointer?.done();
  return JSON.stringify({ done: `已把 ${label} 指给用户看，屏幕上高亮约 6 秒`, position: `屏幕${screenArea(el)}` });
}

/** 元素在屏幕上的大致方位（上中下 × 左中右），给回答描述位置用。 */
const AREAS = [
  ['左上方', '上方中间', '右上方'],
  ['左侧', '中间', '右侧'],
  ['左下方', '下方中间', '右下方'],
];
function screenArea(el: Element): string {
  const { x, y } = center(el);
  const third = (v: number, size: number) => Math.min(2, Math.max(0, Math.floor((v / size) * 3)));
  return AREAS[third(y, window.innerHeight)]![third(x, window.innerWidth)]!;
}

// ---------------------------------------------------------------- 看

const LOOK_MAX_SIDE = 1280;

/** 截取元素（默认最上层的弹窗或主内容区）的图片，缩到长边 LOOK_MAX_SIDE 以内的 JPEG。 */
export async function lookAt(ref?: string): Promise<{ content: string; images?: string[] }> {
  const modal = topModal();
  let target: Element = modal ? modalBox(modal) : mainRoot();
  if (ref) {
    const el = resolve(ref);
    if (typeof el === 'string') return { content: JSON.stringify({ error: el }) };
    target = el;
  }
  const label = ref ? describe(target) : '当前页面';
  await pointAt(target, label, 'look');
  try {
    const r = target.getBoundingClientRect();
    const scale = Math.min(1, LOOK_MAX_SIDE / Math.max(r.width, r.height, 1));
    const { domToJpeg } = await import('modern-screenshot');
    const url = await domToJpeg(target, { scale, quality: 0.75, filter: (n) => !(n instanceof Element && ownUi(n)) });
    return { content: JSON.stringify({ done: `截了${label}的图，图片附在后面` }), images: [url] };
  } catch {
    return { content: JSON.stringify({ error: '截图失败（页面里可能有跨域图片），改用 read_page 读文字' }) };
  } finally {
    pointer?.done();
  }
}
