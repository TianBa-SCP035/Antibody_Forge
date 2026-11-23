<script lang="ts" setup>
import { ref, watch } from 'vue';

import { cn } from '@vben-core/shared/utils';

interface Props {
  class?: string;
  minLoadingTime?: number;
  spinning?: boolean;
}

defineOptions({
  name: 'VbenSpinner',
});

const props = withDefaults(defineProps<Props>(), {
  minLoadingTime: 0,
});

const showSpinner = ref(false);
const renderSpinner = ref(false);
const fading = ref(false);
const timer = ref<ReturnType<typeof setTimeout>>();

watch(
  () => props.spinning,
  (show) => {
    clearTimeout(timer.value);
    if (!show) {
      fading.value = true;
      showSpinner.value = false;
      return;
    }

    const reveal = () => {
      fading.value = false;
      showSpinner.value = true;
      renderSpinner.value = true;
    };

    if (props.minLoadingTime > 0) {
      timer.value = setTimeout(reveal, props.minLoadingTime);
      return;
    }
    reveal();
  },
  {
    immediate: true,
  },
);

function onTransitionEnd(event: TransitionEvent) {
  if (event.propertyName !== 'opacity' || event.target !== event.currentTarget) {
    return;
  }
  if (!showSpinner.value) {
    renderSpinner.value = false;
  }
}
</script>

<template>
  <div
    :class="
      cn(
        'flex-center bg-background absolute top-0 left-0 z-100 size-full',
        fading ? 'transition-opacity duration-300' : '',
        showSpinner ? 'opacity-100' : 'pointer-events-none opacity-0',
        props.class,
      )
    "
    @transitionend="onTransitionEnd"
  >
    <div
      v-if="renderSpinner"
      class="loader before:bg-primary/50 after:bg-primary relative size-12 before:absolute before:top-15 before:left-0 before:h-1.25 before:w-12 before:rounded-full before:content-[''] after:absolute after:top-0 after:left-0 after:h-full after:w-full after:rounded after:content-['']"
    ></div>
  </div>
</template>

<style scoped>
.loader {
  transform: translateZ(0);
  will-change: transform;

  &::before {
    animation: loader-shadow-ani 0.5s linear infinite;
  }

  &::after {
    animation: loader-jump-ani 0.5s linear infinite;
  }
}

@keyframes loader-jump-ani {
  25% {
    transform: translateY(9px) rotate(22.5deg);
  }

  50% {
    transform: translateY(18px) scale(1, 0.9) rotate(45deg);
  }

  75% {
    transform: translateY(9px) rotate(67.5deg);
  }

  100% {
    transform: translateY(0) rotate(90deg);
  }
}

@keyframes loader-shadow-ani {
  0%,
  100% {
    transform: scale(1, 1);
  }

  50% {
    transform: scale(1.2, 1);
  }
}
</style>
