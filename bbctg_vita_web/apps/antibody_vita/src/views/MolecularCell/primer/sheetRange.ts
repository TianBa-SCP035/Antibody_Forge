import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';

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
  let rafId = 0;

  const colIndexByKey = new Map<string, number>();
  options.columns.forEach((col, index) => {
    colIndexByKey.set(col.key, index);
  });

  const rowIndexMap = computed(() => {
    const map = new Map<string, number>();
    const list = options.rows.value || [];
    for (let i = 0; i < list.length; i += 1) {
      const row = list[i];
      if (row?.id != null) map.set(String(row.id), i);
    }
    return map;
  });

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

  function getColIndexByColId(colid: string | null) {
    if (!colid) return undefined;
    const field = table()?.getColumnById?.(colid)?.field;
    return field ? colIndexByKey.get(field) : undefined;
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
    const bodyWrapper =
      wrap.querySelector('.vxe-table--main-wrapper .vxe-table--body-wrapper') ||
      wrap.querySelector('.vxe-table--body-wrapper');
    const tbody = bodyWrapper?.querySelector('tbody');
    if (!bodyWrapper || !tbody) {
      overlay.style.display = 'none';
      return;
    }
    const rows = rowIndexMap.value;
    let topTr: Element | null = null;
    let bottomTr: Element | null = null;
    let topRow = Number.POSITIVE_INFINITY;
    let bottomRow = Number.NEGATIVE_INFINITY;
    for (const tr of Array.from(tbody.children)) {
      const rowid = tr.getAttribute('rowid');
      if (!rowid) continue;
      const rowIndex = rows.get(String(rowid));
      if (rowIndex == null || rowIndex < current.r1 || rowIndex > current.r2) continue;
      if (rowIndex < topRow) {
        topRow = rowIndex;
        topTr = tr;
      }
      if (rowIndex > bottomRow) {
        bottomRow = rowIndex;
        bottomTr = tr;
      }
    }
    if (!topTr || !bottomTr) {
      overlay.style.display = 'none';
      return;
    }
    let leftTd: Element | null = null;
    let rightTd: Element | null = null;
    let leftCol = Number.POSITIVE_INFINITY;
    let rightCol = Number.NEGATIVE_INFINITY;
    for (const cell of Array.from(topTr.children)) {
      const colIndex = getColIndexByColId(cell.getAttribute('colid'));
      if (colIndex == null || colIndex < current.c1 || colIndex > current.c2) continue;
      if (colIndex < leftCol) {
        leftCol = colIndex;
        leftTd = cell;
      }
      if (colIndex > rightCol) {
        rightCol = colIndex;
        rightTd = cell;
      }
    }
    if (!leftTd || !rightTd) {
      overlay.style.display = 'none';
      return;
    }
    const stageRect = stage.getBoundingClientRect();
    const bodyRect = bodyWrapper.getBoundingClientRect();
    let clipLeft = bodyRect.left;
    let clipRight = bodyRect.right;
    const clipTop = bodyRect.top;
    const clipBottom = bodyRect.bottom;
    const fixedLeft = wrap.querySelector('.vxe-table--fixed-left-wrapper');
    if (fixedLeft) {
      const flRect = fixedLeft.getBoundingClientRect();
      if (flRect.width > 1) clipLeft = Math.max(clipLeft, flRect.right);
    }
    const fixedRight = wrap.querySelector('.vxe-table--fixed-right-wrapper');
    if (fixedRight) {
      const frRect = fixedRight.getBoundingClientRect();
      if (frRect.width > 1) clipRight = Math.min(clipRight, frRect.left);
    }
    const topRect = topTr.getBoundingClientRect();
    const bottomRect = bottomTr.getBoundingClientRect();
    const leftRect = leftTd.getBoundingClientRect();
    const rightRect = rightTd.getBoundingClientRect();
    const rowH = topRect.height || 40;
    const colW = leftRect.width || 120;
    const rawTop = topRow > current.r1 ? topRect.top - (topRow - current.r1) * rowH : topRect.top;
    const rawBottom =
      bottomRow < current.r2 ? bottomRect.bottom + (current.r2 - bottomRow) * rowH : bottomRect.bottom;
    const rawLeft = leftCol > current.c1 ? leftRect.left - (leftCol - current.c1) * colW : leftRect.left;
    const rawRight =
      rightCol < current.c2 ? rightRect.right + (current.c2 - rightCol) * colW : rightRect.right;

    const left = Math.max(rawLeft, clipLeft);
    const top = Math.max(rawTop, clipTop);
    const right = Math.min(rawRight, clipRight);
    const bottom = Math.min(rawBottom, clipBottom);
    if (right <= left || bottom <= top) {
      overlay.style.display = 'none';
      return;
    }
    overlay.style.display = 'block';
    overlay.style.width = `${right - left + 2}px`;
    overlay.style.height = `${bottom - top + 2}px`;
    overlay.style.transform = `translate3d(${left - stageRect.left - 1}px, ${top - stageRect.top - 1}px, 0)`;
  }

  function schedulePaint() {
    if (rafId) return;
    rafId = requestAnimationFrame(() => {
      rafId = 0;
      syncOverlay();
    });
  }

  function setRange(next: SheetRange) {
    const prev = range.value;
    if (
      prev &&
      prev.r1 === next.r1 &&
      prev.c1 === next.c1 &&
      prev.r2 === next.r2 &&
      prev.c2 === next.c2
    ) {
      return;
    }
    range.value = next;
    schedulePaint();
  }

  function clearRange() {
    range.value = null;
    pointerDown = false;
    dragMode = '';
    table()?.clearSelected?.();
    schedulePaint();
  }

  function hitCell(target: EventTarget | null): CellHit | null {
    const cell = (target as HTMLElement | null)?.closest?.('.vxe-body--column');
    if (!cell) return null;
    const $table = table();
    const column = $table?.getColumnById?.(cell.getAttribute('colid'));
    const field = column?.field;
    const colIndex = field ? (colIndexByKey.get(field) ?? -1) : -1;
    if (!field || colIndex < 0) return null;
    const tr = cell.closest('tr');
    const rowid = tr?.getAttribute('rowid');
    let rowIndex = rowid != null ? (rowIndexMap.value.get(String(rowid)) ?? -1) : -1;
    if (rowIndex < 0 && tr && $table?.getRowNode) {
      const row = $table.getRowNode(tr)?.item;
      if (row?.id != null) rowIndex = rowIndexMap.value.get(String(row.id)) ?? -1;
    }
    return rowIndex < 0 ? null : { rowIndex, colIndex, field };
  }

  function hitHeader(target: EventTarget | null) {
    const header = (target as HTMLElement | null)?.closest?.('.vxe-header--column');
    if (!header) return null;
    const column = table()?.getColumnById?.(header.getAttribute('colid'));
    const colIndex = column?.field ? (colIndexByKey.get(column.field) ?? -1) : -1;
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
    if (row) {
      const selected = table()?.getSelectedCell?.();
      if (!selected || selected.row !== row || selected.column?.field !== hit.field) {
        table()?.setSelectCell?.(row, hit.field);
      }
    }
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
    syncOverlay();
    schedulePaint();
  }

  function onCellSelected(payload: { row: T; column?: { field?: string }; $event?: Event }) {
    const native = payload.$event;
    if (pointerDown || native?.type !== 'keydown') return;
    const key = payload.column?.field;
    const rowIndex = payload.row?.id != null ? (rowIndexMap.value.get(String(payload.row.id)) ?? -1) : -1;
    const colIndex = key ? (colIndexByKey.get(key) ?? -1) : -1;
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
    window.addEventListener('resize', schedulePaint);
  });
  onBeforeUnmount(() => {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
    window.removeEventListener('mouseup', finishPointer);
    window.removeEventListener('resize', schedulePaint);
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
