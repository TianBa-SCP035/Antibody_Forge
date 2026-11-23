export const HIDDEN_CHARS = /[\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g;
export const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;

export interface CleanFieldTextOptions {
  keepBreaks?: boolean;
}

/** 去掉不换行空格、零宽字符和控制字符；keepBreaks 时保留换行（制表符换成空格），否则压成一行。 */
export function cleanFieldText(
  value: unknown,
  { keepBreaks = false }: CleanFieldTextOptions = {},
): string {
  const text = String(value ?? '')
    .replace(/\u00A0/g, ' ')
    .replace(HIDDEN_CHARS, '')
    .replace(CONTROL_CHARS, '');
  if (keepBreaks) {
    return text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/\t+/g, ' ')
      .replace(/^[ \n]+|[ \n]+$/g, '');
  }
  return text.replace(/[\r\n\t]+/g, ' ').trim();
}
