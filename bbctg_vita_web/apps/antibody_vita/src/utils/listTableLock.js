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
  let bodyChildObserver = null
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

  function optimizeTableScroll(body) {
    if (!(body instanceof HTMLElement) || body.classList.contains('is-list-table-defer-body')) return
    const vms = getElTableVms(body)
    for (const vm of vms) {
      // 1. Element Plus 2.13 的固定列已采用原生 CSS position: sticky（同处一个 <tr> 内），
      //    禁用 setHoverRow mutation（改由纯 CSS tr:hover > td 高亮），
      //    彻底消除滚动时鼠标划过行触发的 watch(hoverRow) -> Array.from(el.children) 500 行扫描
      if (vm.store?.states?.isComplex) {
        vm.store.states.isComplex.value = false
      }
      if (vm.store?.states?.hoverRow && vm.store.states.hoverRow.value !== null) {
        vm.store.states.hoverRow.value = null
      }
      if (vm.store?.mutations && !vm.store._vbenHoverPatched) {
        vm.store._vbenHoverPatched = true
        vm.store.mutations.setHoverRow = () => {}
      }

      // 2. 锁定根容器为 is-scrolling-none（彻底阻断 EP 在横滑时切换根容器 class 导致 5.7 万节点样式失效 + 左固定列 border-right:none 引发 520ms 全表重排），
      //    同时在 .el-table__inner-wrapper 上挂载 2 个独立 GPU 合成层叶子阴影条（左/右各 1 个 div，替代原来的 1000 个 td::before），
      //    仅在阴影显隐布尔状态真正变化时才更新 opacity，保证表头与表体 100% 同步满帧滚动。
      const tableWrapper = vm.refs?.tableWrapper
      if (tableWrapper && !tableWrapper._vbenScrollClassPatched) {
        tableWrapper._vbenScrollClassPatched = true
        const innerWrapper = tableWrapper.querySelector('.el-table__inner-wrapper')
        let leftShadow = null
        let rightShadow = null
        let lastShowLeft = null
        let lastShowRight = null
        if (innerWrapper instanceof HTMLElement) {
          leftShadow = document.createElement('div')
          leftShadow.className = 'vben-table-scroll-shadow-left'
          leftShadow.style.cssText =
            'position:absolute;top:0;bottom:0;width:10px;pointer-events:none;z-index:3;opacity:0;transform:translateZ(0);transition:opacity 0.15s ease;background:linear-gradient(to right, rgba(0,0,0,0.08), transparent);'
          rightShadow = document.createElement('div')
          rightShadow.className = 'vben-table-scroll-shadow-right'
          rightShadow.style.cssText =
            'position:absolute;top:0;bottom:0;width:10px;pointer-events:none;z-index:3;opacity:0;transform:translateZ(0);transition:opacity 0.15s ease;background:linear-gradient(to left, rgba(0,0,0,0.08), transparent);'
          innerWrapper.append(leftShadow, rightShadow)
        }

        const syncShadowGeometry = () => {
          if (!leftShadow || !rightShadow) return
          const firstRow =
            tableWrapper.querySelector('.el-table__header-wrapper tr')
            || tableWrapper.querySelector('.el-table__body-wrapper tbody tr')
          const leftFixed = firstRow?.querySelector('.el-table-fixed-column--left.is-last-column')
          const rightFixed = firstRow?.querySelector('.el-table-fixed-column--right.is-first-column')
          if (leftFixed instanceof HTMLElement && leftFixed.offsetWidth > 0) {
            leftShadow.style.display = ''
            leftShadow.style.left = `${leftFixed.offsetLeft + leftFixed.offsetWidth}px`
          } else {
            leftShadow.style.display = 'none'
          }
          if (rightFixed instanceof HTMLElement && rightFixed.offsetWidth > 0) {
            rightShadow.style.display = ''
            rightShadow.style.right = `${rightFixed.offsetWidth}px`
          } else {
            rightShadow.style.display = 'none'
          }
        }
        syncShadowGeometry()
        tableWrapper._vbenSyncShadowGeometry = syncShadowGeometry

        const updateShadowVisibility = (cls) => {
          if (typeof cls !== 'string') return
          const showLeft = cls.includes('is-scrolling-middle') || cls.includes('is-scrolling-right')
          const showRight = cls.includes('is-scrolling-middle') || cls.includes('is-scrolling-left')
          if (leftShadow && showLeft !== lastShowLeft) {
            lastShowLeft = showLeft
            leftShadow.style.opacity = showLeft ? '1' : '0'
          }
          if (rightShadow && showRight !== lastShowRight) {
            lastShowRight = showRight
            rightShadow.style.opacity = showRight ? '1' : '0'
          }
        }
        updateShadowVisibility(tableWrapper.className)

        const rawClassList = tableWrapper.classList
        const cleanClassName = Array.from(rawClassList)
          .filter((c) => !c.startsWith('is-scrolling-'))
          .concat('is-scrolling-none')
          .join(' ')
        rawClassList.value = cleanClassName
        let lockedClassName = cleanClassName

        Object.defineProperty(tableWrapper, 'className', {
          configurable: true,
          get() {
            return lockedClassName
          },
          set(val) {
            if (typeof val === 'string') {
              updateShadowVisibility(val)
              const next = val.replace(/is-scrolling-(left|middle|right)/g, 'is-scrolling-none')
              if (next === lockedClassName) return
              lockedClassName = next
              rawClassList.value = next
            }
          },
        })

        // 3. 表头跟手 + 滚动期间拦住 mouseenter 强制回流。
        //    表体继续走合成器滚动（不拦截 wheel、不改 scrollLeft）。
        //    非固定表头单元格用 ScrollTimeline 按表体横向滚动进度做 translate，和表体同一帧绘制。
        //    固定列保持 position: sticky，不参与这层位移。
        //    表头/表脚的 scrollLeft 写入被空操作吃掉，避免 Element Plus 再滚一次把单元格错开。
        //    没有 ScrollTimeline 时才退回主线程滚轮同步。
        const scrollWrap =
          vm.refs?.scrollBarRef?.wrapRef
          || tableWrapper.querySelector('.el-table__body-wrapper .el-scrollbar__wrap')
        const headerWrapper =
          vm.refs?.headerWrapper
          || tableWrapper.querySelector('.el-table__header-wrapper')
        const footerWrapper =
          vm.refs?.footerWrapper
          || tableWrapper.querySelector('.el-table__footer-wrapper')
        if (scrollWrap instanceof HTMLElement && !scrollWrap._vbenSyncPatched) {
          scrollWrap._vbenSyncPatched = true
          let scrollingUntil = 0
          const markScrolling = () => {
            scrollingUntil = performance.now() + 100
          }
          scrollWrap.addEventListener('scroll', markScrolling, { passive: true })
          scrollWrap.addEventListener('wheel', markScrolling, { passive: true })
          scrollWrap.addEventListener(
            'mouseenter',
            (e) => {
              if (performance.now() < scrollingUntil) {
                e.stopPropagation()
              }
            },
            true,
          )

          const scrollLeftDesc = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollLeft')
          const lockScrollLeft = (el) => {
            if (!(el instanceof HTMLElement) || el._vbenScrollLocked || !scrollLeftDesc?.get || !scrollLeftDesc?.set) return
            if (scrollLeftDesc.get.call(el) !== 0) {
              scrollLeftDesc.set.call(el, 0)
            }
            Object.defineProperty(el, 'scrollLeft', {
              configurable: true,
              get() {
                return scrollLeftDesc.get.call(this)
              },
              set() {},
            })
            el._vbenScrollLocked = true
          }

          let headerAnims = []
          let lastMax = -1
          const rebuildHeaderSync = () => {
            if (body.classList.contains('is-list-table-defer-body')) return
            const header = headerWrapper?.isConnected
              ? headerWrapper
              : tableWrapper.querySelector('.el-table__header-wrapper')
            const footer = footerWrapper?.isConnected
              ? footerWrapper
              : tableWrapper.querySelector('.el-table__footer-wrapper')
            lockScrollLeft(header)
            lockScrollLeft(footer)
            const max = scrollWrap.scrollWidth - scrollWrap.clientWidth
            const cells = []
            for (const wrap of [header, footer]) {
              if (!(wrap instanceof HTMLElement)) continue
              wrap.querySelectorAll(
                'table.el-table__header > thead > tr > th, table.el-table__header > thead > tr > td, table.el-table__footer > tbody > tr > td',
              ).forEach((cell) => {
                if (
                  cell.classList.contains('gutter')
                  || cell.classList.contains('el-table-fixed-column--left')
                  || cell.classList.contains('el-table-fixed-column--right')
                ) return
                cells.push(cell)
              })
            }
            const sameTargets =
              headerAnims.length === cells.length
              && cells.every((cell, idx) => headerAnims[idx]?.effect?.target === cell)
            if (sameTargets && Math.abs(max - lastMax) < 0.5) return
            lastMax = max
            for (const anim of headerAnims) anim.cancel()
            headerAnims = []
            const ScrollTimelineCtor = globalThis.ScrollTimeline
            if (max <= 1 || typeof ScrollTimelineCtor !== 'function' || cells.length === 0) return
            let timeline
            try {
              timeline = new ScrollTimelineCtor({ source: scrollWrap, axis: 'x' })
            } catch {
              return
            }
            const opts = { timeline, fill: 'both' }
            for (const cell of cells) {
              headerAnims.push(cell.animate(
                [
                  { transform: 'translate3d(0,0,0)' },
                  { transform: `translate3d(${-max}px,0,0)` },
                ],
                opts,
              ))
            }
          }

          if (typeof globalThis.ScrollTimeline === 'function') {
            rebuildHeaderSync()
            tableWrapper._vbenRebuildHeaderSync = rebuildHeaderSync
            const onHeaderOrScrollResize = () => {
              syncShadowGeometry()
              rebuildHeaderSync()
            }
            const ro =
              typeof ResizeObserver === 'function'
                ? new ResizeObserver(onHeaderOrScrollResize)
                : null
            if (ro) {
              ro.observe(scrollWrap)
              const view = scrollWrap.firstElementChild
              if (view instanceof Element) ro.observe(view)
            }
            const mo =
              typeof MutationObserver === 'function' && headerWrapper instanceof HTMLElement
                ? new MutationObserver(onHeaderOrScrollResize)
                : null
            if (mo && headerWrapper instanceof HTMLElement) {
              const thead = headerWrapper.querySelector('thead') || headerWrapper
              mo.observe(thead, { childList: true, subtree: true })
            }
            scrollWrap._vbenHeaderSyncCleanup = () => {
              ro?.disconnect()
              mo?.disconnect()
              for (const anim of headerAnims) anim.cancel()
              headerAnims = []
            }
          } else {
            const desc =
              Object.getOwnPropertyDescriptor(Object.getPrototypeOf(scrollWrap), 'scrollLeft')
              || scrollLeftDesc
            if (desc?.get && desc?.set) {
              Object.defineProperty(scrollWrap, 'scrollLeft', {
                configurable: true,
                get() {
                  return desc.get.call(this)
                },
                set(val) {
                  desc.set.call(this, val)
                  const next = desc.get.call(this)
                  if (headerWrapper instanceof HTMLElement) headerWrapper.scrollLeft = next
                  if (footerWrapper instanceof HTMLElement) footerWrapper.scrollLeft = next
                },
              })
            }
            scrollWrap.addEventListener(
              'wheel',
              (e) => {
                const dx = e.deltaX || (e.shiftKey ? e.deltaY : 0)
                if (dx !== 0 && e.cancelable) {
                  e.preventDefault()
                  scrollWrap.scrollLeft += dx
                }
              },
              { passive: false },
            )
          }
        }
      } else if (tableWrapper) {
        tableWrapper._vbenSyncShadowGeometry?.()
        tableWrapper._vbenRebuildHeaderSync?.()
      }
    }
  }

  function observeBodyTableSwitch(body) {
    if (!(body instanceof HTMLElement) || typeof MutationObserver !== 'function') return
    if (!bodyChildObserver) {
      bodyChildObserver = new MutationObserver((mutations) => {
        const hasTableChange = mutations.some((m) =>
          [...m.addedNodes, ...m.removedNodes].some(
            (n) => n instanceof HTMLElement && !n.classList.contains('vita-iso-load'),
          ),
        )
        if (!hasTableChange || !body.isConnected) return
        bindScrollMemory(body)
        optimizeTableScroll(body)
        requestAnimationFrame(() => {
          if (body.isConnected) {
            bindScrollMemory(body)
            optimizeTableScroll(body)
          }
        })
      })
    }
    bodyChildObserver.disconnect()
    bodyChildObserver.observe(body, { childList: true })
  }

  function bindAndMeasure(body) {
    if (!observer) observer = new ResizeObserver(measure)
    observer.disconnect()
    observer.observe(body)
    observeBodyTableSwitch(body)
    measure()
    bindScrollMemory(body)
    optimizeTableScroll(body)
    // ElTable 在 onMounted -> await nextTick() 后才会执行 store.updateColumns() 渲染固定列并设置 isComplex，
    // 因此在下一帧补充执行一次 optimizeTableScroll，确保固定列阴影几何与 hover 优化 100% 生效
    requestAnimationFrame(() => {
      if (body.isConnected) optimizeTableScroll(body)
    })
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
      bodyChildObserver?.disconnect()
      unbindScrollMemory()
      cancelDefer()
      const body = getBody()
      if (body instanceof HTMLElement) {
        body.classList.remove('is-list-table-defer-body')
        resumeElTables(body)
        optimizeTableScroll(body)
        requestAnimationFrame(() => {
          if (body.isConnected) optimizeTableScroll(body)
        })
      } else {
        nextTick(() => {
          if (currentGen !== lockGen) return
          const nextBody = getBody()
          if (nextBody instanceof HTMLElement) {
            optimizeTableScroll(nextBody)
            requestAnimationFrame(() => {
              if (nextBody.isConnected) optimizeTableScroll(nextBody)
            })
          }
        })
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
      if (savedScrollLeft > 0) {
        const wrap = findScrollWrap(body)
        if (wrap && wrap.scrollLeft !== savedScrollLeft) {
          wrap.scrollLeft = savedScrollLeft
        }
      }
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
    bodyChildObserver?.disconnect()
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
    bodyChildObserver?.disconnect()
    const body = getBody()
    if (body instanceof HTMLElement) {
      body.querySelectorAll('.el-scrollbar__wrap').forEach((wrap) => {
        wrap._vbenHeaderSyncCleanup?.()
      })
    }
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
