import { defineConfig } from '@vben/vite-config';

import { fileURLToPath, URL } from 'node:url';
import ElementPlus from 'unplugin-element-plus/vite';

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
          '/serum-api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/serum-api/, '/api'),
            target: devBackend,
          },
        },
      },
    },
  };
});
