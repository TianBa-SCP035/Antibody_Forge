import { computed, nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { contentOverlayActive } from '@vben-core/composables';

import { preferences } from '@vben/preferences';

function waitFrames(count = 2) {
  return new Promise<void>((resolve) => {
    const step = (left: number) => {
      if (left <= 0) {
        resolve();
        return;
      }
      requestAnimationFrame(() => step(left - 1));
    };
    step(count);
  });
}

function useContentSpinner() {
  const spinning = ref(false);
  const router = useRouter();
  const enableLoading = computed(() => preferences.transition.loading);
  let hideGen = 0;

  const shouldCover = (to: { meta: { loaded?: boolean; iframeSrc?: string } }) =>
    !to.meta.loaded && enableLoading.value && !to.meta.iframeSrc;

  const hideOverlay = (gen: number) => {
    if (gen !== hideGen) {
      return;
    }
    spinning.value = false;
    contentOverlayActive.value = false;
  };

  // 首屏一画完就淡，不等满多少毫秒，也不等表格接口。
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
    spinning.value = true;
    contentOverlayActive.value = true;
    return hideGen;
  };

  router.beforeEach((to, from) => {
    if (to.path === from.path) {
      return true;
    }
    if (shouldCover(to)) {
      cover();
    }
    return true;
  });

  router.afterEach((to) => {
    if (shouldCover(to)) {
      scheduleHide(hideGen);
    }
    return true;
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
