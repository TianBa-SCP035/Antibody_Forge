import { installApiWatch } from './apiWatch';

// Must run before the first page mounts, so the pet sees the list requests pages send on load.
installApiWatch();

export { default as FatFishPet } from './FatFishPet.vue';
export * from './pageContext';
