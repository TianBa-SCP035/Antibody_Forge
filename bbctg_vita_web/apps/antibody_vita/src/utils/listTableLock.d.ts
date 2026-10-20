import type { ComponentOptionsMixin, ComputedRef, Ref } from 'vue'

export const LIST_TABLE_LOCK_MIN: number

export function shouldLockListTable(limit: unknown): boolean

export const listTableLockMixin: ComponentOptionsMixin

export function useListTableLock(getLimit: () => unknown): {
  listTableBody: Ref<HTMLElement | null>
  listTableHeight: Ref<number | undefined>
  listTableLocked: ComputedRef<boolean>
}
