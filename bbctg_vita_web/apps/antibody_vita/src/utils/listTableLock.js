import {
  computed,
  getCurrentInstance,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
  watch,
} from 'vue'

/** 每页达到这个条数后，表格卡片占满一屏并固定表头。20 条仍整页滚动。 */
export const LIST_TABLE_LOCK_MIN = 50

export function shouldLockListTable(limit) {
  return Number(limit) >= LIST_TABLE_LOCK_MIN
}

function createLock(getPage, getBody, setHeight) {
  let observer = null

  function measure() {
    const body = getBody()
    const height = body instanceof HTMLElement ? Math.floor(body.clientHeight) : 0
    setHeight(height > 0 ? height : undefined)
  }

  function watchBody() {
    nextTick(() => {
      requestAnimationFrame(() => {
        const body = getBody()
        if (!(body instanceof HTMLElement)) return
        if (!observer) observer = new ResizeObserver(measure)
        observer.disconnect()
        observer.observe(body)
        measure()
      })
    })
  }

  function apply(locked, retried = false) {
    const page = getPage()
    if (!(page instanceof HTMLElement)) return
    if (!locked) {
      setHeight(undefined)
      observer?.disconnect()
      return
    }
    if (page.offsetParent === null) {
      if (!retried) nextTick(() => apply(true, true))
      return
    }
    watchBody()
  }

  function pause() {
    observer?.disconnect()
  }

  function destroy() {
    observer?.disconnect()
    setHeight(undefined)
  }

  return { apply, destroy, pause }
}

/** 选项式列表页。 */
export const listTableLockMixin = {
  data() {
    return { listTableHeight: undefined }
  },
  computed: {
    listTableLocked() {
      return shouldLockListTable(this.listQuery?.limit ?? this.query?.limit)
    },
  },
  watch: {
    listTableLocked(locked) {
      this._listTableLock?.apply(locked)
    },
  },
  created() {
    this._listTableLock = createLock(
      () => (this.$el instanceof HTMLElement ? this.$el : null),
      () => this.$refs.listTableBody,
      (height) => {
        if (height !== this.listTableHeight) this.listTableHeight = height
      },
    )
  },
  mounted() {
    this._listTableLock.apply(this.listTableLocked)
  },
  activated() {
    this._listTableLock?.apply(this.listTableLocked)
  },
  deactivated() {
    this._listTableLock?.pause()
  },
  beforeUnmount() {
    this._listTableLock?.destroy()
  },
}

/** 组合式列表页。调用时 limit 的响应式来源必须已经存在。 */
export function useListTableLock(getLimit) {
  const instance = getCurrentInstance()
  const listTableHeight = ref(undefined)
  const listTableBody = ref(null)
  const listTableLocked = computed(() => shouldLockListTable(getLimit()))
  const lock = createLock(
    () => {
      const el = instance?.proxy?.$el
      return el instanceof HTMLElement ? el : null
    },
    () => listTableBody.value,
    (height) => {
      if (height !== listTableHeight.value) listTableHeight.value = height
    },
  )

  watch(listTableLocked, (locked) => lock.apply(locked))
  onMounted(() => lock.apply(listTableLocked.value))
  onActivated(() => lock.apply(listTableLocked.value))
  onDeactivated(() => lock.pause())
  onBeforeUnmount(() => lock.destroy())

  return { listTableLocked, listTableHeight, listTableBody }
}
