import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';

export interface SheetColumn {
  key: string;
}

interface SheetRange {
  r1: number;
  c1: number;
  r2: number;
  c2: number;
}

interface CellHit {
  rowIndex: number;
  colIndex: number;
  field: string;
}

/**
 * 表格划选复制。只负责选区和 Ctrl+C，不处理单元格编辑。
 */
export function useSheetRange<T extends { id: number | string }>(options: {
  rows: Ref<T[]>;
  columns: SheetColumn[];
  text: (row: T, key: string) => string;
}) {
  const wrapRef = ref<HTMLElement | null>(null);
  const stageRef = ref<HTMLElement | null>(null);
  const overlayRef = ref<HTMLElement | null>(null);
  const tableRef = ref<any>(null);
  const range = ref<SheetRange | null>(null);
  let pointerDown = false;
  let dragMode: '' | 'cells' | 'columns' = '';

  function table() {
    return tableRef.value;
  }

  function normalized() {
    const current = range.value;
    if (!current) return null;
    return {
      r1: Math.min(current.r1, current.r2),
      c1: Math.min(current.c1, current.c2),
      r2: Math.max(current.r1, current.r2),
      c2: Math.max(current.c1, current.c2),
    };
  }

  function columnIndexById() {
    const map = new Map<string, number>();
    options.columns.forEach((column, index) => {
      const id = table()?.getColumnByField?.(column.key)?.id;
      if (id) map.set(id, index);
    });
    return map;
  }

  function rowIndexById() {
    const $table = table();
    return new Map(
      options.rows.value.map((row, index) => [
        String($table?.getRowid?.(row) || row.id),
        index,
      ]),
    );
  }

  function paint() {
    const wrap = wrapRef.value;
    const overlay = overlayRef.value;
    if (!wrap || !overlay) return;
    overlay.classList.remove('is-scrolling');
    wrap.querySelectorAll('.is-sheet-selected').forEach((el) => {
      el.classList.remove('is-sheet-selected');
    });
    const current = normalized();
    const $table = table();
    if (!current || !$table) {
      overlay.style.display = 'none';
      return;
    }
    const rows = rowIndexById();
    const columns = columnIndexById();
    for (const tr of wrap.querySelectorAll('.vxe-table--body-wrapper tr[rowid]')) {
      const rowIndex = rows.get(String(tr.getAttribute('rowid') || ''));
      if (rowIndex == null || rowIndex < current.r1 || rowIndex > current.r2) continue;
      for (const cell of tr.querySelectorAll('.vxe-body--column')) {
        const colIndex = columns.get(cell.getAttribute('colid') || '');
        if (colIndex == null || colIndex < current.c1 || colIndex > current.c2) continue;
        cell.classList.add('is-sheet-selected');
      }
    }
    syncOverlay();
  }

  function syncOverlay() {
    const wrap = wrapRef.value;
    const overlay = overlayRef.value;
    const stage = stageRef.value;
    const current = normalized();
    if (!wrap || !overlay || !stage || !current) {
      if (overlay) overlay.style.display = 'none';
      return;
    }
    const rows = rowIndexById();
    const columns = columnIndexById();
    let top = Number.POSITIVE_INFINITY;
    let left = Number.POSITIVE_INFINITY;
    let right = Number.NEGATIVE_INFINITY;
    let bottom = Number.NEGATIVE_INFINITY;
    let first: Element | null = null;
    for (const tr of wrap.querySelectorAll('.vxe-table--body-wrapper tr[rowid]')) {
      const rowIndex = rows.get(String(tr.getAttribute('rowid') || ''));
      if (rowIndex == null || rowIndex < current.r1 || rowIndex > current.r2) continue;
      for (const cell of tr.querySelectorAll('.vxe-body--column')) {
        const colIndex = columns.get(cell.getAttribute('colid') || '');
        if (colIndex == null || colIndex < current.c1 || colIndex > current.c2) continue;
        const rect = cell.getBoundingClientRect();
        if (rect.width <= 1 || rect.height <= 1) continue;
        first ||= cell;
        top = Math.min(top, rect.top);
        left = Math.min(left, rect.left);
        right = Math.max(right, rect.right);
        bottom = Math.max(bottom, rect.bottom);
      }
    }
    const stageRect = stage.getBoundingClientRect();
    const bodyRect = first?.closest('.vxe-table--body-wrapper')?.getBoundingClientRect();
    if (!bodyRect || !first || right <= left || bottom <= top) {
      overlay.style.display = 'none';
      return;
    }
    const clipLeft = Math.max(left, bodyRect.left);
    const clipTop = Math.max(top, bodyRect.top);
    const clipRight = Math.min(right, bodyRect.right);
    const clipBottom = Math.min(bottom, bodyRect.bottom);
    if (clipRight <= clipLeft || clipBottom <= clipTop) {
      overlay.style.display = 'none';
      return;
    }
    overlay.style.display = 'block';
    overlay.style.width = `${clipRight - clipLeft + 2}px`;
    overlay.style.height = `${clipBottom - clipTop + 2}px`;
    overlay.style.transform = `translate3d(${clipLeft - stageRect.left - 1}px, ${clipTop - stageRect.top - 1}px, 0)`;
  }

  function setRange(next: SheetRange) {
    range.value = next;
    requestAnimationFrame(paint);
  }

  function clearRange() {
    range.value = null;
    pointerDown = false;
    dragMode = '';
    table()?.clearSelected?.();
    requestAnimationFrame(paint);
  }

  function hitCell(target: EventTarget | null): CellHit | null {
    const cell = (target as HTMLElement | null)?.closest?.('.vxe-body--column');
    if (!cell) return null;
    const $table = table();
    const column = $table?.getColumnById?.(cell.getAttribute('colid'));
    const field = column?.field;
    const colIndex = options.columns.findIndex((item) => item.key === field);
    if (!field || colIndex < 0) return null;
    const tr = cell.closest('tr');
    const row = tr && $table?.getRowNode ? $table.getRowNode(tr)?.item : null;
    const rowIndex = row
      ? options.rows.value.findIndex((item) => item.id === row.id)
      : options.rows.value.findIndex((item) => String(item.id) === String(tr?.getAttribute('rowid')));
    return rowIndex < 0 ? null : { rowIndex, colIndex, field };
  }

  function hitHeader(target: EventTarget | null) {
    const header = (target as HTMLElement | null)?.closest?.('.vxe-header--column');
    if (!header) return null;
    const column = table()?.getColumnById?.(header.getAttribute('colid'));
    const colIndex = options.columns.findIndex((item) => item.key === column?.field);
    return colIndex < 0 ? null : colIndex;
  }

  function focusWrap() {
    wrapRef.value?.focus({ preventScroll: true });
  }

  function onContextMenu(event: MouseEvent) {
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea')) return;
    event.preventDefault();
    clearRange();
  }

  function onMouseDown(event: MouseEvent) {
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea, button, .el-button, a')) return;
    if (target?.closest('.vxe-cell--col-resizable')) return;
    focusWrap();
    if (event.button !== 0) return;
    const headerIndex = hitHeader(event.target);
    if (headerIndex != null && options.rows.value.length) {
      event.preventDefault();
      window.getSelection()?.removeAllRanges();
      dragMode = 'columns';
      pointerDown = true;
      const start = event.shiftKey && range.value ? range.value.c1 : headerIndex;
      setRange({ r1: 0, c1: start, r2: options.rows.value.length - 1, c2: headerIndex });
      return;
    }
    const hit = hitCell(event.target);
    if (!hit) return;
    event.preventDefault();
    window.getSelection()?.removeAllRanges();
    dragMode = 'cells';
    pointerDown = true;
    if (event.shiftKey && range.value) {
      setRange({ ...range.value, r2: hit.rowIndex, c2: hit.colIndex });
    } else {
      setRange({ r1: hit.rowIndex, c1: hit.colIndex, r2: hit.rowIndex, c2: hit.colIndex });
    }
    const row = options.rows.value[hit.rowIndex];
    if (row) table()?.setSelectCell?.(row, hit.field);
  }

  function onMouseOver(event: MouseEvent) {
    if (!pointerDown || !range.value) return;
    if (dragMode === 'columns') {
      const headerIndex = hitHeader(event.target);
      if (headerIndex == null || headerIndex === range.value.c2) return;
      setRange({ ...range.value, c2: headerIndex });
      return;
    }
    const hit = hitCell(event.target);
    if (!hit) return;
    if (hit.rowIndex === range.value.r2 && hit.colIndex === range.value.c2) return;
    setRange({ ...range.value, r2: hit.rowIndex, c2: hit.colIndex });
  }

  function onSelectStart(event: Event) {
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea')) return;
    event.preventDefault();
  }

  function onScroll() {
    if (!range.value) return;
    overlayRef.value?.classList.add('is-scrolling');
    syncOverlay();
  }

  function onCellSelected(payload: { row: T; column?: { field?: string }; $event?: Event }) {
    const native = payload.$event;
    if (pointerDown || native?.type !== 'keydown') return;
    const key = payload.column?.field;
    const rowIndex = options.rows.value.findIndex((item) => item.id === payload.row.id);
    const colIndex = options.columns.findIndex((item) => item.key === key);
    if (rowIndex < 0 || colIndex < 0) return;
    const extend = Boolean(
      'shiftKey' in native && (native as KeyboardEvent).shiftKey
      && (native as KeyboardEvent).key.startsWith('Arrow'),
    );
    if (extend && range.value) {
      setRange({ ...range.value, r2: rowIndex, c2: colIndex });
      return;
    }
    setRange({ r1: rowIndex, c1: colIndex, r2: rowIndex, c2: colIndex });
  }

  function selectAll() {
    if (!options.rows.value.length || !options.columns.length) return;
    setRange({
      r1: 0,
      c1: 0,
      r2: options.rows.value.length - 1,
      c2: options.columns.length - 1,
    });
    focusWrap();
  }

  function onKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea')) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      selectAll();
    }
  }

  function rangeText() {
    const current = normalized();
    if (!current) return '';
    const lines: string[] = [];
    for (let rowIndex = current.r1; rowIndex <= current.r2; rowIndex += 1) {
      const row = options.rows.value[rowIndex];
      if (!row) continue;
      const cells: string[] = [];
      for (let colIndex = current.c1; colIndex <= current.c2; colIndex += 1) {
        const column = options.columns[colIndex];
        if (!column) continue;
        cells.push(options.text(row, column.key));
      }
      lines.push(cells.join('\t'));
    }
    return lines.join('\n');
  }

  function onCopy(event: ClipboardEvent) {
    const text = rangeText();
    const target = event.target as HTMLElement | null;
    if (!text || target?.closest('input, textarea')) return;
    event.preventDefault();
    event.clipboardData?.setData('text/plain', text);
  }

  function finishPointer() {
    pointerDown = false;
    dragMode = '';
  }

  watch(options.rows, () => clearRange());

  onMounted(() => {
    window.addEventListener('mouseup', finishPointer);
    window.addEventListener('resize', paint);
  });
  onBeforeUnmount(() => {
    window.removeEventListener('mouseup', finishPointer);
    window.removeEventListener('resize', paint);
  });

  return {
    wrapRef,
    stageRef,
    overlayRef,
    tableRef,
    onContextMenu,
    onMouseDown,
    onMouseOver,
    onSelectStart,
    onScroll,
    onCellSelected,
    onKeydown,
    onCopy,
  };
}
