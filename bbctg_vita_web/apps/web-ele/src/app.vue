<script lang="ts" setup>
// import { useElementPlusDesignTokens } from '@vben/hooks';

import { ElConfigProvider } from 'element-plus';

import { elementLocale } from '#/locales';

defineOptions({ name: 'App' });

// Temporarily disable Vben's Element Plus theme variable overrides.
// useElementPlusDesignTokens();
</script>

<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView />
  </ElConfigProvider>
</template>


