import { installApiWatch } from './apiWatch';

// 必须在首个页面挂载前执行，才能观察页面加载时发出的列表请求。
installApiWatch();

export { default as FatFishPet } from './FatFishPet.vue';
export * from './pageContext';
