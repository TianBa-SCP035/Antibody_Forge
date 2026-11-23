<script lang="ts" setup>
import { ElConfigProvider } from 'element-plus';

import { FatFishPet } from '#/components/fatfish';
import { elementLocale } from '#/locales';

defineOptions({ name: 'App' });
</script>

<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView />
    <FatFishPet />
  </ElConfigProvider>
</template>


