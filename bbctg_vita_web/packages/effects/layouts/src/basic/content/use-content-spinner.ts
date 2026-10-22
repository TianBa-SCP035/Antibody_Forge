import { computed, nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  contentOverlayActive,
  contentOverlayBlocking,
} from '@vben-core/composables';

import { preferences } from '@vben/preferences';

const FADE_OUT_MS = 300;

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
  let zIndexTimer: ReturnType<typeof setTimeout> | undefined;

  const shouldCover = (to: { meta: { loaded?: boolean; iframeSrc?: string } }) =>
    !to.meta.loaded && enableLoading.value && !to.meta.iframeSrc;

  const hideOverlay = (gen: number) => {
    if (gen !== hideGen) {
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
    void nextTick(async () => {
      await waitFrames(2);
      if (gen !== hideGen) {
        return;
      }
      hideOverlay(gen);
    });
  };

  const cover = () => {
    hideGen += 1;
    clearTimeout(zIndexTimer);
    spinning.value = true;
    contentOverlayActive.value = true;
    contentOverlayBlocking.value = true;
    return hideGen;
  };

  router.beforeEach(async (to, from) => {
    if (to.path === from.path) {
      return true;
    }
    activeNavTarget = to.fullPath || to.path;
    if (shouldCover(to)) {
      const gen = cover();
      // 站内切页时先等待双 rAF 确保轻量遮罩已真实绘制上屏，再挂载底层新页面
      if (from.matched.length > 0) {
        await nextTick();
        await waitFrames(2);
        if (gen !== hideGen) return true;
      }
    }
    return true;
  });

  router.afterEach((to, _from, failure) => {
    const target = to.fullPath || to.path;
    // 若旧导航因并发新导航被取消（aborted），且新导航已接管，则不能关掉新导航的遮罩
    if (failure && activeNavTarget && activeNavTarget !== target) {
      return true;
    }
    if (spinning.value || shouldCover(to)) {
      scheduleHide(hideGen);
    }
    return true;
  });

  router.onError(() => {
    if (spinning.value) {
      hideOverlay(hideGen);
    }
  });

  onMounted(() => {
    const route = router.currentRoute.value;
    if (!spinning.value && shouldCover(route)) {
      scheduleHide(cover());
    }
  });

  return { spinning };
}

export { useContentSpinner };
