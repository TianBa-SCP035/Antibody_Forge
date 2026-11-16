let pendingDiscoveryId = ''

/** 别的页面跳到发现工作台前记下要定位的发现编号，工作台进页或切回时取走一次。 */
export function rememberDiscoveryFocus(discoveryId) {
  pendingDiscoveryId = String(discoveryId || '').trim()
}

export function hasDiscoveryFocus() {
  return Boolean(pendingDiscoveryId)
}

export function takeDiscoveryFocus() {
  const discoveryId = pendingDiscoveryId
  pendingDiscoveryId = ''
  return discoveryId
}
