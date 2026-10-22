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

function collectElTableVmsFromVNode(rootVNode, bodyEl, out = new Set()) {
  if (!rootVNode || typeof rootVNode !== 'object') return out
  const comp = rootVNode.component
  if (comp) {
    const compEl = comp.vnode?.el
    if (comp.state?.doLayout && comp.layout && (!bodyEl || (compEl instanceof Node && bodyEl.contains(compEl)))) {
      out.add(comp)
    }
    if (comp.subTree) {
      collectElTableVmsFromVNode(comp.subTree, bodyEl, out)
    }
  }
  const children = rootVNode.children
  if (Array.isArray(children)) {
    for (const child of children) {
      collectElTableVmsFromVNode(child, bodyEl, out)
    }
  }
  return out
}

function createLock(getPage, getBody, setHeight, onBodyResumed, getHostInternalInstance) {
  let observer = null
  let lockGen = 0
  let deferGen = 0
  let rafId = 0
  let deferRaf1 = 0
  let deferRaf2 = 0
  let deferRaf3 = 0
  let deferTimer = 0
  let deferTransitionTarget = null
  let deferTransitionHandler = null
  let deferOverlayEl = null
  let deferFadeTimer = 0
  let scrollEl = null
  let savedScrollTop = 0
  let savedScrollLeft = 0
  let knownHeight = 0

  function onScroll() {
    if (!scrollEl) return
    savedScrollTop = scrollEl.scrollTop
    savedScrollLeft = scrollEl.scrollLeft
  }

  function unbindScrollMemory() {
    if (scrollEl) {
      scrollEl.removeEventListener('scroll', onScroll)
      scrollEl = null
    }
  }

  function showDeferOverlay(body) {
    if (!(body instanceof HTMLElement)) return
    if (deferFadeTimer) {
      clearTimeout(deferFadeTimer)
      deferFadeTimer = 0
    }
    if (!deferOverlayEl) {
      const overlay = document.createElement('div')
      overlay.className = 'vita-iso-load is-on'
      overlay.setAttribute('aria-hidden', 'true')
      const box = document.createElement('div')
      box.className = 'vita-iso-load__box'
      box.innerHTML = '<div class="vita-iso-load__spin"></div>'
      overlay.append(box)
      deferOverlayEl = overlay
    }
    deferOverlayEl.classList.add('is-on')
    if (deferOverlayEl.parentElement !== body) {
      body.append(deferOverlayEl)
    }
  }

  function hideDeferOverlay(immediate = false) {
    if (deferFadeTimer) {
      clearTimeout(deferFadeTimer)
      deferFadeTimer = 0
    }
    if (!deferOverlayEl) return
    if (immediate) {
      deferOverlayEl.remove()
      deferOverlayEl = null
      return
    }
    deferOverlayEl.classList.remove('is-on')
    const el = deferOverlayEl
    deferFadeTimer = window.setTimeout(() => {
      deferFadeTimer = 0
      if (!el.classList.contains('is-on')) {
        el.remove()
        if (deferOverlayEl === el) deferOverlayEl = null
      }
    }, 240)
  }

  function cancelDefer() {
    if (deferRaf1) {
      cancelAnimationFrame(deferRaf1)
      deferRaf1 = 0
    }
    if (deferRaf2) {
      cancelAnimationFrame(deferRaf2)
      deferRaf2 = 0
    }
    if (deferRaf3) {
      cancelAnimationFrame(deferRaf3)
      deferRaf3 = 0
    }
    if (deferTimer) {
      clearTimeout(deferTimer)
      deferTimer = 0
    }
    if (deferTransitionTarget && deferTransitionHandler) {
      deferTransitionTarget.removeEventListener('transitionend', deferTransitionHandler)
      deferTransitionTarget = null
      deferTransitionHandler = null
    }
  }

  function findScrollWrap(body) {
    if (!(body instanceof HTMLElement)) return null
    return (
      body.querySelector('.vxe-table--body-wrapper.body--wrapper')
      || body.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
      || body.querySelector('.el-table__body-wrapper')
    )
  }

  function bindScrollMemory(body) {
    const nextScrollEl = findScrollWrap(body)
    if (nextScrollEl !== scrollEl) {
      scrollEl?.removeEventListener('scroll', onScroll)
      scrollEl = nextScrollEl
      scrollEl?.addEventListener('scroll', onScroll, { passive: true })
    }
    if (scrollEl && (savedScrollTop > 0 || savedScrollLeft > 0)) {
      if (scrollEl.scrollTop !== savedScrollTop) scrollEl.scrollTop = savedScrollTop
      if (scrollEl.scrollLeft !== savedScrollLeft) scrollEl.scrollLeft = savedScrollLeft
    }
  }

  function cancelPendingRaf() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = 0
    }
  }

  function measure() {
    const body = getBody()
    const height = body instanceof HTMLElement ? Math.floor(body.clientHeight) : 0
    if (height > 0) knownHeight = height
    setHeight(height > 0 ? height : undefined)
  }

  function bindAndMeasure(body) {
    if (!observer) observer = new ResizeObserver(measure)
    observer.disconnect()
    observer.observe(body)
    measure()
    bindScrollMemory(body)
  }

  function watchBody(currentGen) {
    const immediateBody = getBody()
    if (immediateBody instanceof HTMLElement && immediateBody.clientHeight > 0) {
      bindAndMeasure(immediateBody)
      return
    }
    nextTick(() => {
      if (currentGen !== lockGen) return
      cancelPendingRaf()
      rafId = requestAnimationFrame(() => {
        rafId = 0
        if (currentGen !== lockGen) return
        const rafBody = getBody()
        if (!(rafBody instanceof HTMLElement)) return
        bindAndMeasure(rafBody)
      })
    })
  }

  function getElTableVms(body) {
    if (!(body instanceof HTMLElement)) return []
    const hostVm = getHostInternalInstance?.()
    const vms = hostVm?.subTree ? collectElTableVmsFromVNode(hostVm.subTree, body) : new Set()
    const tables = body.querySelectorAll('.el-table')
    for (const tableEl of tables) {
      const vm = tableEl.__vueParentComponent
      if (vm?.state?.doLayout) vms.add(vm)
    }
    return [...vms]
  }

  function pauseElTables(body) {
    const vms = getElTableVms(body)
    for (const vm of vms) {
      if (vm && vm.$ready) {
        vm.$ready = false
        vm._vbenPausedReady = true
      }
    }
  }

  function resumeElTables(body) {
    if (!(body instanceof HTMLElement)) return
    const vms = getElTableVms(body)
    for (const vm of vms) {
      if (vm && vm._vbenPausedReady) {
        const tableEl = vm.vnode?.el
        const rs = vm.state?.resizeState?.value
        const w = tableEl instanceof HTMLElement ? tableEl.offsetWidth : 0
        const h = tableEl instanceof HTMLElement ? tableEl.offsetHeight : 0
        const headerEl = tableEl instanceof HTMLElement ? tableEl.querySelector('.el-table__header-wrapper') : null
        const hh = headerEl ? headerEl.offsetHeight : (rs?.headerHeight ?? 0)
        const widthChanged = w > 0 && rs && rs.width !== w
        if (rs && w > 0) {
          rs.width = w
          rs.height = h
          rs.headerHeight = hh
        }
        vm.$ready = true
        vm._vbenPausedReady = false
        if (widthChanged) {
          vm.state?.doLayout?.()
        }
      }
    }
  }

  function apply(locked, retried = false, retryGen = 0) {
    const currentGen = retried ? retryGen : ++lockGen
    if (currentGen !== lockGen) return
    cancelPendingRaf()
    const page = getPage()
    if (!(page instanceof HTMLElement)) return
    if (!locked) {
      observer?.disconnect()
      unbindScrollMemory()
      cancelDefer()
      const body = getBody()
      if (body instanceof HTMLElement) {
        body.classList.remove('is-list-table-defer-body')
        resumeElTables(body)
      }
      hideDeferOverlay(true)
      knownHeight = 0
      setHeight(undefined)
      return
    }
    const body = getBody()
    // 从 KeepAlive 缓存重新激活且处于表体延迟显现阶段、已知锁定高度时：
    // 跳过点击帧的 offsetParent / clientHeight 同步强制布局（layoutMs = 0），待进场动画结束后再重绑 ResizeObserver
    if (knownHeight > 0 && body instanceof HTMLElement && body.classList.contains('is-list-table-defer-body')) {
      setHeight(knownHeight)
      return
    }
    if (page.offsetParent === null) {
      if (!retried) {
        nextTick(() => {
          if (currentGen !== lockGen) return
          apply(true, true, currentGen)
        })
      }
      return
    }
    watchBody(currentGen)
  }

  /**
   * 严格的退场 -> 进场 -> 表格显现三段式顺序：
   * 1. 离开锁高大表时冻结 el-table $ready（避免离屏 0x0 触发 ResizeObserver -> doLayout 重算 500 行），
   *    并通过纯 DOM class（is-list-table-defer-body）隐藏 tbody 并挂上局部转圈，绝不销毁/重建 Vue VNode；
   * 2. 切回该标签页时，整页固定骨架与表格转圈先以满帧 60fps 完成 320ms 进场滑入动画；
   * 3. 仅在页面进场动画彻底结束后（transitionend + 1帧），才原位显现 tbody、恢复 $ready 与滚动位置并淡出转圈。
   */
  function resumeRows(locked) {
    cancelDefer()
    const currentDeferGen = ++deferGen
    const body = getBody()
    if (!locked || !(body instanceof HTMLElement) || !body.classList.contains('is-list-table-defer-body')) {
      if (body instanceof HTMLElement) {
        body.classList.remove('is-list-table-defer-body')
        resumeElTables(body)
      }
      hideDeferOverlay(true)
      return
    }
    showDeferOverlay(body)
    const page = getPage()
    let done = false

    const finishResume = () => {
      if (done || currentDeferGen !== deferGen) return
      done = true
      cancelDefer()
      // 等 Vue Transition 移除 enter-active 后的下一帧再原位显现 tbody，确保整页绝不会二次播放进场动画
      deferRaf2 = requestAnimationFrame(() => {
        deferRaf2 = 0
        if (currentDeferGen !== deferGen) return
        const curBody = getBody()
        if (curBody instanceof HTMLElement) {
          curBody.classList.remove('is-list-table-defer-body')
          bindAndMeasure(curBody)
        }
        hideDeferOverlay(false)
        onBodyResumed?.()
        // 在 tbody 显现并跑完当帧 ResizeObserver 后的下一帧再恢复 $ready，避免高度变化触发多余 doLayout
        deferRaf3 = requestAnimationFrame(() => {
          deferRaf3 = 0
          if (currentDeferGen !== deferGen) return
          const b = getBody()
          if (b instanceof HTMLElement) resumeElTables(b)
        })
      })
    }

    if (page instanceof HTMLElement) {
      const onTransitionEnd = (event) => {
        if (event.target !== page) return
        finishResume()
      }
      deferTransitionTarget = page
      deferTransitionHandler = onTransitionEnd
      page.addEventListener('transitionend', onTransitionEnd)
    }

    // 兜底定时器（略长于 2帧起播 + 320ms 进场过渡时长，确保不会早于动画结束）
    deferTimer = window.setTimeout(finishResume, 380)

    // 若用户关闭了页面过渡动画（页面无 *-enter-active class），则无需等待 380ms，在下一帧直接显现
    deferRaf1 = requestAnimationFrame(() => {
      deferRaf1 = 0
      if (done || currentDeferGen !== deferGen) return
      const hasEnterTransition =
        page instanceof HTMLElement
        && Array.from(page.classList).some((cls) => cls.endsWith('-enter-active'))
      if (!hasEnterTransition) {
        finishResume()
      }
    })
  }

  function pause(locked) {
    lockGen += 1
    deferGen += 1
    cancelPendingRaf()
    cancelDefer()
    observer?.disconnect()
    unbindScrollMemory()
    const body = getBody()
    pauseElTables(body)
    if (!locked) return
    if (body instanceof HTMLElement && body.querySelector('.el-table__body-wrapper')) {
      body.classList.add('is-list-table-defer-body')
      showDeferOverlay(body)
    }
  }

  function destroy() {
    lockGen += 1
    deferGen += 1
    cancelPendingRaf()
    cancelDefer()
    observer?.disconnect()
    unbindScrollMemory()
    hideDeferOverlay(true)
    setHeight(undefined)
  }

  return { apply, destroy, pause, resumeRows }
}

/** 选项式列表页。 */
export const listTableLockMixin = {
  data() {
    return {
      listTableHeight: undefined,
    }
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
      () => {
        this.onListTableBodyResumed?.()
      },
      () => this.$,
    )
  },
  mounted() {
    this._listTableLock.apply(this.listTableLocked)
  },
  activated() {
    this._listTableLock?.apply(this.listTableLocked)
    this._listTableLock?.resumeRows(this.listTableLocked)
  },
  deactivated() {
    this._listTableLock?.pause(this.listTableLocked)
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
    undefined,
    () => instance,
  )

  watch(listTableLocked, (locked) => lock.apply(locked))
  onMounted(() => lock.apply(listTableLocked.value))
  onActivated(() => {
    lock.apply(listTableLocked.value)
    lock.resumeRows(listTableLocked.value)
  })
  onDeactivated(() => lock.pause(listTableLocked.value))
  onBeforeUnmount(() => lock.destroy())

  return { listTableLocked, listTableHeight, listTableBody }
}
