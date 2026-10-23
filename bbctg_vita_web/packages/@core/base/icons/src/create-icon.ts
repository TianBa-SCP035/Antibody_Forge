import { defineComponent, h } from 'vue';

import { Icon } from '@iconify/vue';

import './local-icons';

/**
 * 默认开启 ssr: true，使 @iconify/vue 在首帧 setup 阶段即从本地已注册的图标集中同步渲染出 <svg>，
 * 消除默认等到 onMounted 后才异步二次渲染导致的「文字先显示、图标慢半拍蹦出」现象。
 */
const IconifyIcon = defineComponent({
  name: 'IconifyIcon',
  inheritAttrs: false,
  setup(_props, { attrs }) {
    return () => h(Icon, { ssr: true, ...attrs } as any);
  },
});

function createIconifyIcon(icon: string) {
  return defineComponent({
    name: `Icon-${icon}`,
    inheritAttrs: false,
    setup(props, { attrs }) {
      return () => h(Icon, { icon, ssr: true, ...props, ...attrs } as any);
    },
  });
}

export { createIconifyIcon, IconifyIcon };
