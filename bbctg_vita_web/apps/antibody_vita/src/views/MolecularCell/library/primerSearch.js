export const SEARCH_STEPS = ['primer', 'both', 'left', 'right']
const FLANK_GAP = '......'

const ARM_BY_DIRECTION = {
  F: ['ACCGAGATCTACAC', 'ACACTCTTTCC'],
  R: ['GGCATACGAGAT', 'GTGACTGGAGTT'],
}

export function normalizeSequence(value) {
  return String(value || '').toUpperCase().replace(/[^ACGTN]/g, '')
}

export function reverseComplement(value) {
  const complement = { A: 'T', C: 'G', G: 'C', T: 'A', N: 'N' }
  return normalizeSequence(value)
    .split('')
    .reverse()
    .map((base) => complement[base] || base)
    .join('')
}

export function armPair(direction) {
  return ARM_BY_DIRECTION[direction] || []
}

function flankParts(value) {
  const raw = String(value || '')
  if (!/[.。]/.test(raw)) return null
  const parts = raw.split(/[.。]+/).map((part) => normalizeSequence(part))
  if (parts.length !== 2 || parts.some((part) => !part)) return null
  return parts
}

export function searchTarget(query, complementOn) {
  const flanks = flankParts(query)
  if (flanks) {
    const pair = complementOn
      ? [reverseComplement(flanks[1]), reverseComplement(flanks[0])]
      : flanks
    return { flank: true, left: pair[0], right: pair[1] }
  }
  const written = normalizeSequence(query)
  return { flank: false, term: complementOn ? reverseComplement(written) : written }
}

export function complementQueryText(query) {
  const target = searchTarget(query, true)
  if (target.flank) return `${target.left}${FLANK_GAP}${target.right}`
  return target.term
}

export function pairSearch(kind, armIndex) {
  return kind === 'flank' || (kind === 'arm' && armIndex === 2)
}

export function matchCount(length, paired) {
  return Math.floor(length / (paired ? 2 : 1))
}

export function matchSpans(matches, index, paired) {
  if (index < 0 || !matches.length) return []
  return matches.slice(index, index + (paired ? 2 : 1))
}

export function readDirectionInfo(direction, status, observed, target) {
  if (direction !== 'F' && direction !== 'R') {
    return { label: '方向未识别', arrow: '↔', tone: 'unknown' }
  }
  const end = direction === 'F' ? 'i5 端' : 'i7 端'
  let flipped = null
  if (status === 'matched' || status === 'arm_only') flipped = false
  else if (status === 'matched_rc' || status === 'arm_only_rc') flipped = true
  else {
    const sequence = normalizeSequence(observed)
    const expected = normalizeSequence(target)
    if (sequence && expected && sequence.includes(expected)) flipped = false
    else if (sequence && expected && sequence.includes(reverseComplement(expected))) flipped = true
  }
  if (flipped === null) return { label: end, arrow: '', tone: 'unknown' }
  const forward = (direction === 'F') !== flipped
  return {
    label: `${forward ? '正向' : '反向'} · ${end}`,
    arrow: forward ? '→' : '←',
    tone: forward ? 'forward' : 'reverse',
  }
}

export function searchSummaryText(kind, armIndex, count, index, query) {
  if (pairSearch(kind, armIndex)) {
    const places = Math.floor(count / 2)
    if (!places) return '两侧 未找到'
    const here = Math.floor(index / 2) + 1
    return places > 1 ? `两侧 ${here}/${places}` : '两侧 1 处'
  }
  if (kind === 'arm') {
    const label = armIndex === 1 ? '右臂' : '左臂'
    return count ? `${label} ${index + 1}/${count}` : `${label} 未找到`
  }
  if (!normalizeSequence(query)) return ''
  if (!count) return '未找到'
  return `找到 ${index + 1}/${count}`
}

function locateArms(haystack, pair) {
  if (!haystack || pair.length < 2) return { step: 'primer', complement: false }
  const [left, right] = pair
  const directLeft = haystack.includes(left)
  const directRight = haystack.includes(right)
  const rcLeft = haystack.includes(reverseComplement(left))
  const rcRight = haystack.includes(reverseComplement(right))
  if (directLeft && directRight) return { step: 'both', complement: false }
  if (rcLeft && rcRight) return { step: 'both', complement: true }
  if (directLeft) return { step: 'left', complement: false }
  if (directRight) return { step: 'right', complement: false }
  if (rcLeft) return { step: 'left', complement: true }
  if (rcRight) return { step: 'right', complement: true }
  return { step: 'primer', complement: false }
}

function queryForStep(step, direction, target) {
  const pair = armPair(direction)
  if (step === 'both' && pair.length === 2) return `${pair[0]}${FLANK_GAP}${pair[1]}`
  if (step === 'left') return pair[0] || ''
  if (step === 'right') return pair[1] || ''
  return normalizeSequence(target)
}

export function viewForStep(step, direction, target) {
  const query = queryForStep(step, direction, target)
  return {
    step,
    stepIndex: Math.max(0, SEARCH_STEPS.indexOf(step)),
    armIndex: step === 'left' ? 0 : step === 'right' ? 1 : step === 'both' ? 2 : 0,
    query,
    kind: step === 'primer' ? (query ? 'primer' : 'manual') : 'arm',
  }
}

export function openingSearch(status, direction, observed, target) {
  const pair = armPair(direction)
  let step = 'primer'
  let complement = status === 'matched_rc' || status === 'arm_only_rc'
  if (status === 'arm_only' || status === 'arm_only_rc') step = 'both'
  else if (status !== 'matched' && status !== 'matched_rc') {
    const found = locateArms(normalizeSequence(observed), pair)
    step = found.step
    complement = found.complement
  }
  return { ...viewForStep(step, direction, target), complement }
}
