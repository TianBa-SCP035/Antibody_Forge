import { defineConfig } from '@vben/vite-config';

import { fileURLToPath, URL } from 'node:url';
import ElementPlus from 'unplugin-element-plus/vite';

/**
 * vxe 自带的 `[class*="vxe-"] *::before/::after` 让页面上任意元素改 class 都要重算全部后代样式，
 * 大表格时每次约 70ms。伪元素的 border-box 已由 Tailwind 预设覆盖，构建时去掉这两个选择器。
 */
function stripVxeDescendantPseudo() {
  const pattern = /\[class\*=["']?vxe-["']?\]\s+\*?::?(?:after|before)/;
  return {
    postcssPlugin: 'strip-vxe-descendant-pseudo',
    Rule(rule: { remove: () => void; selector: string; selectors: string[] }) {
      if (!rule.selector.includes('vxe-')) return;
      const kept = rule.selectors.filter((selector) => !pattern.test(selector));
      if (kept.length === rule.selectors.length) return;
      if (kept.length === 0) rule.remove();
      else rule.selectors = kept;
    },
  };
}

function defaultDevBackend(mode: string): string {
  if (mode === 'test') {
    return 'http://127.0.0.1:9527';
  }
  if (mode === 'production') {
    return 'http://127.0.0.1:8848';
  }
  return 'http://127.0.0.1:8888';
}

export default defineConfig(async (env) => {
  const mode = env?.mode ?? 'development';
  const devBackend =
    process.env.VITA_DEV_BACKEND?.trim() || defaultDevBackend(mode);

  return {
    application: {},
    vite: {
      css: {
        postcss: {
          plugins: [stripVxeDescendantPseudo()],
        },
      },
      plugins: [
        ElementPlus({
          format: 'esm',
        }),
      ],
      resolve: {
        alias: {
          '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
      },
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            target: devBackend,
          },
        },
      },
    },
  };
});
