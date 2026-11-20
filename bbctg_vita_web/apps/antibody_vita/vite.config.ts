import { defineConfig } from '@vben/vite-config';

import { existsSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
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

/** 与 unplugin-element-plus 注入的写法一致；optimizeDeps 的通配符匹配不到 element-plus 的 exports 映射，只能逐个列出。 */
function elementPlusStyleEntries(): string[] {
  const dir = join(dirname(createRequire(import.meta.url).resolve('element-plus/package.json')), 'es/components');
  return readdirSync(dir)
    .filter((name) => existsSync(join(dir, name, 'style/css.mjs')))
    .map((name) => `element-plus/es/components/${name}/style/css`);
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
      // 组件样式由 unplugin-element-plus 按需引入，开发时第一次进某个页面才被发现，Vite 会因此整页刷新
      // （正在进行的请求和宠物的操作都会断掉）。启动时一次性预构建全部样式入口。
      optimizeDeps: {
        include: elementPlusStyleEntries(),
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
          // Must be before '/api' — otherwise the whole /api prefix hits the business backend.
          '/api/pet': {
            changeOrigin: true,
            target: 'http://127.0.0.1:18765',
          },
          '/api': {
            changeOrigin: true,
            target: devBackend,
          },
        },
      },
    },
  };
});
