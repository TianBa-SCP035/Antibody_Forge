/** 预置两个系列。自建系列不在这里登记，有引物后由接口返回。 */
export const PRESET_LIBRARIES = [
  { value: '达普Barcode', hint: '达普仪器', tone: 'stat-purple' },
  { value: 'UDP', hint: '其他仪器或步骤', tone: 'stat-orange' },
] as const;

const EXTRA_TONES = ['stat-teal', 'stat-gray'] as const;

const COMPLEMENT: Record<string, string> = { A: 'T', C: 'G', G: 'C', T: 'A', N: 'N' };

export function libraryHint(name: string) {
  return PRESET_LIBRARIES.find((item) => item.value === name)?.hint || '自建';
}

export function libraryTone(name: string, index: number) {
  return PRESET_LIBRARIES.find((item) => item.value === name)?.tone
    || EXTRA_TONES[index % EXTRA_TONES.length];
}

export function cleanSequence(value: string) {
  return value.replace(/\s+/g, '').toUpperCase();
}

export function checkSequence(value: string) {
  return cleanSequence(value)
    .split('')
    .reverse()
    .map((base) => COMPLEMENT[base] || '')
    .join('');
}

export function directionLabel(value?: null | string) {
  if (value === 'F') return '正向';
  if (value === 'R') return '反向';
  return '';
}
