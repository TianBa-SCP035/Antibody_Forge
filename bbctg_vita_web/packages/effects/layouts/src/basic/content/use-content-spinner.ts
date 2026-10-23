import { computed, nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  contentOverlayActive,
  contentOverlayBlocking,
} from '@vben-core/composables';

import { preferences } from '@vben/preferences';

const FADE_OUT_MS = 300;
const SHOW_DELAY_MS = 120;

function waitFrames(count = 2) {
  return new Promise<void>((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      resolve();
    };
    const step = (left: number) => {
      if (left <= 0) {
        finish();
        return;
      }
      requestAnimationFrame(() => step(left - 1));
    };
    step(count);
    setTimeout(finish, count * 24 + 16);
  });
}

function useContentSpinner() {
  const spinning = ref(false);
  const router = useRouter();
  const enableLoading = computed(() => preferences.transition.loading);
  let hideGen = 0;
  let activeNavTarget = '';
  let showTimer: ReturnType<typeof setTimeout> | undefined;
  let zIndexTimer: ReturnType<typeof setTimeout> | undefined;

  const shouldCover = (to: { meta: { loaded?: boolean; iframeSrc?: string } }) =>
    !to.meta.loaded && enableLoading.value && !to.meta.iframeSrc;

  const hideOverlay = (gen: number) => {
    if (gen !== hideGen) {
      return;
    }
    clearTimeout(showTimer);
    showTimer = undefined;
    if (!spinning.value) {
      contentOverlayBlocking.value = false;
      contentOverlayActive.value = false;
      return;
    }
    spinning.value = false;
    contentOverlayBlocking.value = false;
    clearTimeout(zIndexTimer);
    zIndexTimer = setTimeout(() => {
      if (gen !== hideGen) return;
      contentOverlayActive.value = false;
    }, FADE_OUT_MS);
  };

  // 新页面完成首帧排版后淡出遮罩，且淡出瞬间即释放鼠标点击/滚动
  const scheduleHide = (gen: number) => {
    clearTimeout(showTimer);
    showTimer = undefined;
    if (!spinning.value) {
      hideOverlay(gen);
      return;
    }
    void nextTick(async () => {
      await waitFrames(1);
      if (gen !== hideGen) {
        return;
      }
      hideOverlay(gen);
    });
  };

  const revealOverlay = () => {
    spinning.value = true;
    contentOverlayActive.value = true;
    contentOverlayBlocking.value = true;
  };

  const cover = (delayed = false) => {
    hideGen += 1;
    const gen = hideGen;
    clearTimeout(showTimer);
    clearTimeout(zIndexTimer);
    if (!delayed) {
      revealOverlay();
      return gen;
    }
    // 站内点击左侧菜单首次进页时：不阻塞 beforeEach，且仅当异步路由分包超过 120ms 仍未解析完时才显现全局遮罩；
    // 正常秒开的页面直接播放 320ms fade-slide 进场动画，避免实心白底遮罩吞掉页面过渡动画。
    showTimer = setTimeout(() => {
      showTimer = undefined;
      if (gen !== hideGen) return;
      revealOverlay();
    }, SHOW_DELAY_MS);
    return gen;
  };

  router.beforeEach((to, from) => {
    if (to.path === from.path) {
      return true;
    }
    activeNavTarget = to.fullPath || to.path;
    if (shouldCover(to)) {
      cover(from.matched.length > 0);
    }
    return true;
  });

  router.afterEach((to, _from, failure) => {
    const target = to.fullPath || to.path;
    // 若旧导航因并发新导航被取消（aborted），且新导航已接管，则不能关掉新导航的遮罩
    if (failure && activeNavTarget && activeNavTarget !== target) {
      return true;
    }
    scheduleHide(hideGen);
    return true;
  });

  router.onError(() => {
    hideOverlay(hideGen);
  });

  onMounted(() => {
    const route = router.currentRoute.value;
    if (!spinning.value && shouldCover(route)) {
      scheduleHide(cover(false));
    }
  });

  return { spinning };
}

export { useContentSpinner };
