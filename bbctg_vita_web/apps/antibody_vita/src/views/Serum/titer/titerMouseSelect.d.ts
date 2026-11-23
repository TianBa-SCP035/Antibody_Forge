export function mouseSampleCode(category?: unknown, mouseNo?: unknown): string
export const PLATE_COLUMN_LIST: number[]
export const TITER_MOUSE_IDENTITY_FIELDS: Array<{ key: string; label: string; kind: string }>
export function miceInGroup(group: Record<string, unknown>): Array<{ no?: string; alive?: boolean }>
export function mouseSlotsInRect(startNo: number, endNo: number): number[]
export function selectionKey(groupId: string, mouseIndex: number): string
export function buildPlateGroup(group: Record<string, unknown>, selectedKeys: Set<string>): Record<string, unknown>
export function titerOrderIdentityFields(order: Record<string, unknown> | null | undefined): unknown[]
