/**
 * 不依赖样式库生成带样式的 .xlsx。SheetJS CE 写入时会丢弃样式，因此在此生成各部件，
 * 再用其内置 CFB 打包。文本单元格均为内联字符串，以「=」开头的内容不会执行。
 * 格式只由数据形态决定，包括数字、占比、短分类、长文本和合计行。
 */
import type { Cell } from './reportBuilder';

export type XlsxSheet = {
  name: string;
  columns: string[];
  rows: Cell[][];
  /** 最后一行为合计行：加粗，且不纳入筛选范围和分类配色。 */
  totalRow?: boolean;
  /** 自由文本工作表（说明）：自动换行，不启用筛选或冻结。 */
  notes?: boolean;
};

const FONT = '微软雅黑';
const HEAD_BG = '1F4E79';
const BORDER = 'D9E2F3';
const ZEBRA = 'F7F9FC';
const TOTAL_BG = 'E8EEF7';
const CATEGORY_BG = ['D6EAF8', 'D5F5E3', 'FDEBD0', 'FADBD8', 'E8DAEF', 'FCF3CF', 'D1F2EB', 'EAEDED'];
const MAX_CATEGORY_COLS = 2;
const MAX_WIDTH = 50;
const PCT_HEAD = /[（(]%[)）]$/;
const BAD_XML = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g;

const NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const NS_PKG = 'http://schemas.openxmlformats.org/package/2006/relationships';
const HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

function esc(v: string): string {
  return v.replace(BAD_XML, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function colName(i: number): string {
  let s = '';
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

function textWidth(v: Cell): number {
  let w = 0;
  for (const ch of v == null ? '' : String(v)) w += /[\u0000-\u00ff]/.test(ch) ? 1 : 2;
  return w;
}

type Xf = { bold?: boolean; size?: number; white?: boolean; fill?: string; numFmt?: number; align: 'left' | 'center'; wrap?: boolean };

/** 返回 xml 在 list 中的索引，首次出现时追加。 */
function intern(list: string[], xml: string): number {
  const at = list.indexOf(xml);
  return at >= 0 ? at : list.push(xml) - 1;
}

const fontXml = (bold: boolean, size: number, white: boolean) =>
  `<font>${bold ? '<b/>' : ''}<sz val="${size}"/><color rgb="FF${white ? 'FFFFFF' : '000000'}"/><name val="${FONT}"/><family val="2"/><charset val="134"/></font>`;

/** 管理 styles.xml 的字体、填充和单元格格式；各集合索引 0 为工作簿默认值。 */
class Styles {
  private fonts = [fontXml(false, 10, false)];
  private fills = ['<fill><patternFill patternType="none"/></fill>', '<fill><patternFill patternType="gray125"/></fill>'];
  private xfs = ['<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'];

  /** 所有带样式的单元格均使用细边框。 */
  id(x: Xf): number {
    const font = intern(this.fonts, fontXml(!!x.bold, x.size ?? 10, !!x.white));
    const fill = x.fill
      ? intern(this.fills, `<fill><patternFill patternType="solid"><fgColor rgb="FF${x.fill}"/><bgColor indexed="64"/></patternFill></fill>`)
      : 0;
    return intern(
      this.xfs,
      `<xf numFmtId="${x.numFmt ?? 0}" fontId="${font}" fillId="${fill}" borderId="1" xfId="0"` +
        ` applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">` +
        `<alignment horizontal="${x.align}" vertical="center"${x.wrap ? ' wrapText="1"' : ''}/></xf>`,
    );
  }

  xml(): string {
    const side = (s: string) => `<${s} style="thin"><color rgb="FF${BORDER}"/></${s}>`;
    return (
      `${HEAD}<styleSheet xmlns="${NS}">` +
      `<numFmts count="2"><numFmt numFmtId="164" formatCode="0.0%"/><numFmt numFmtId="165" formatCode="#,##0.00"/></numFmts>` +
      `<fonts count="${this.fonts.length}">${this.fonts.join('')}</fonts>` +
      `<fills count="${this.fills.length}">${this.fills.join('')}</fills>` +
      `<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>` +
      `<border>${side('left')}${side('right')}${side('top')}${side('bottom')}<diagonal/></border></borders>` +
      `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
      `<cellXfs count="${this.xfs.length}">${this.xfs.join('')}</cellXfs>` +
      `<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>` +
      `</styleSheet>`
    );
  }
}

type ColKind = {
  numeric: boolean;
  integer: boolean;
  /** 存在保留两位小数会显示为 0.00 的值时，保持常规格式。 */
  tiny: boolean;
  pct: boolean;
  center: boolean;
  colours?: Map<string, string>;
  width: number;
};

function classify(sheet: XlsxSheet): ColKind[] {
  const body = sheet.totalRow ? sheet.rows.slice(0, -1) : sheet.rows;
  let categories = 0;
  return sheet.columns.map((head, c) => {
    const values = body.map((r) => r[c]).filter((v) => v != null && v !== '');
    const numeric = values.length > 0 && values.every((v) => typeof v === 'number');
    const all = sheet.rows.map((r) => r[c]).filter((v): v is number => typeof v === 'number');
    const integer = numeric && all.every((v) => Number.isInteger(v));
    const width = Math.max(textWidth(head) + 4, ...sheet.rows.slice(0, 300).map((r) => textWidth(r[c] ?? null)));
    const kind: ColKind = {
      numeric,
      integer,
      tiny: numeric && all.some((v) => v !== 0 && Math.abs(v) < 0.01),
      pct: numeric && PCT_HEAD.test(head),
      center: numeric || width <= 14,
      width: Math.min(MAX_WIDTH, Math.max(8, width + 2)),
    };
    if (!numeric && !sheet.notes && categories < MAX_CATEGORY_COLS && body.length >= 6) {
      const distinct = [...new Set(values.map(String))].filter((v) => v !== '(空)');
      if (distinct.length >= 2 && distinct.length <= CATEGORY_BG.length && body.length >= distinct.length * 2 && width <= 20) {
        kind.colours = new Map(distinct.map((v, i) => [v, CATEGORY_BG[i]!]));
        categories += 1;
      }
    }
    return kind;
  });
}

function sheetXml(sheet: XlsxSheet, styles: Styles, selected: boolean): { xml: string; filter?: string } {
  const kinds = classify(sheet);
  const last = colName(Math.max(0, sheet.columns.length - 1));
  const lastRow = sheet.rows.length + 1;
  const head = styles.id({ bold: true, size: 11, white: true, fill: HEAD_BG, align: 'center' });
  const rowsXml: string[] = [];
  rowsXml.push(
    `<row r="1" ht="24" customHeight="1">${sheet.columns
      .map((h, c) => {
        const label = kinds[c]!.pct ? h.replace(PCT_HEAD, '') : h;
        return `<c r="${colName(c)}1" s="${head}" t="inlineStr"><is><t xml:space="preserve">${esc(label)}</t></is></c>`;
      })
      .join('')}</row>`,
  );
  sheet.rows.forEach((row, i) => {
    const r = i + 2;
    const total = sheet.totalRow && i === sheet.rows.length - 1;
    const cells = sheet.columns.map((_, c) => {
      const k = kinds[c]!;
      let v = row[c] ?? null;
      const numeric = typeof v === 'number' && Number.isFinite(v);
      if (numeric && k.pct) v = (v as number) / 100;
      const fill = total ? TOTAL_BG : (!numeric && v != null && k.colours?.get(String(v))) || (i % 2 === 0 ? ZEBRA : undefined);
      const s = styles.id({
        bold: total,
        fill,
        numFmt: numeric ? (k.pct ? 164 : k.integer ? 3 : k.tiny ? 0 : 165) : 0,
        align: k.center && !sheet.notes ? 'center' : 'left',
        wrap: sheet.notes,
      });
      const ref = `${colName(c)}${r}`;
      if (v == null || v === '') return `<c r="${ref}" s="${s}"/>`;
      if (numeric) return `<c r="${ref}" s="${s}"><v>${v}</v></c>`;
      return `<c r="${ref}" s="${s}" t="inlineStr"><is><t xml:space="preserve">${esc(String(v))}</t></is></c>`;
    });
    rowsXml.push(`<row r="${r}">${cells.join('')}</row>`);
  });

  const freezeCol = !sheet.notes && sheet.columns.length >= 8;
  const pane = sheet.notes
    ? ''
    : freezeCol
      ? '<pane xSplit="1" ySplit="1" topLeftCell="B2" activePane="bottomRight" state="frozen"/><selection pane="bottomRight" activeCell="B2" sqref="B2"/>'
      : '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft" activeCell="A2" sqref="A2"/>';
  const filterEnd = sheet.totalRow ? lastRow - 1 : lastRow;
  const filter = !sheet.notes && filterEnd >= 2 ? `A1:${last}${filterEnd}` : undefined;
  const cols = kinds
    .map((k, c) => `<col min="${c + 1}" max="${c + 1}" width="${sheet.notes && c === kinds.length - 1 ? 100 : k.width}" customWidth="1"/>`)
    .join('');
  const xml =
    `${HEAD}<worksheet xmlns="${NS}" xmlns:r="${NS_R}">` +
    `<dimension ref="A1:${last}${lastRow}"/>` +
    `<sheetViews><sheetView showGridLines="0"${selected ? ' tabSelected="1"' : ''} workbookViewId="0">${pane}</sheetView></sheetViews>` +
    `<sheetFormatPr defaultRowHeight="18" customHeight="1"/>` +
    `<cols>${cols}</cols>` +
    `<sheetData>${rowsXml.join('')}</sheetData>` +
    (filter ? `<autoFilter ref="${filter}"/>` : '') +
    `</worksheet>`;
  return { xml, filter };
}

export async function writeXlsx(sheets: XlsxSheet[]): Promise<Uint8Array<ArrayBuffer>> {
  const { CFB } = await import('xlsx');
  const styles = new Styles();
  const zip = CFB.utils.cfb_new();
  const utf8 = new TextEncoder();
  const add = (path: string, xml: string) => CFB.utils.cfb_add(zip, path, utf8.encode(xml));
  const names: string[] = [];
  sheets.forEach((s, i) => {
    const { xml, filter } = sheetXml(s, styles, i === 0);
    add(`xl/worksheets/sheet${i + 1}.xml`, xml);
    if (filter) {
      const abs = filter.replace(/([A-Z]+)(\d+)/g, '$$$1$$$2');
      names.push(`<definedName name="_xlnm._FilterDatabase" localSheetId="${i}" hidden="1">'${esc(s.name.replace(/'/g, "''"))}'!${abs}</definedName>`);
    }
  });
  add(
    '[Content_Types].xml',
    `${HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
      `<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>` +
      sheets
        .map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`)
        .join('') +
      `</Types>`,
  );
  add(
    '_rels/.rels',
    `${HEAD}<Relationships xmlns="${NS_PKG}"><Relationship Id="rId1" Type="${NS_R}/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
  );
  add(
    'xl/workbook.xml',
    `${HEAD}<workbook xmlns="${NS}" xmlns:r="${NS_R}"><bookViews><workbookView activeTab="0"/></bookViews><sheets>` +
      sheets.map((s, i) => `<sheet name="${esc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('') +
      `</sheets>${names.length ? `<definedNames>${names.join('')}</definedNames>` : ''}</workbook>`,
  );
  add(
    'xl/_rels/workbook.xml.rels',
    `${HEAD}<Relationships xmlns="${NS_PKG}">` +
      sheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${NS_R}/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('') +
      `<Relationship Id="rId${sheets.length + 1}" Type="${NS_R}/styles" Target="styles.xml"/></Relationships>`,
  );
  add('xl/styles.xml', styles.xml());
  return new Uint8Array(CFB.write(zip, { fileType: 'zip', type: 'array', compression: true }));
}
