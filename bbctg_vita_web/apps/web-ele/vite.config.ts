import { defineConfig } from '@vben/vite-config';

import { fileURLToPath, URL } from 'node:url';
import ElementPlus from 'unplugin-element-plus/vite';

export default defineConfig(async () => {
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
            rewrite: (path) => path.replace(/^\/api/, ''),
            // mock代理目标地址
            target: 'http://localhost:5320/api',
            ws: true,
          },
          '/serum-api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/serum-api/, ''),
            target: 'http://127.0.0.1:9091',
          },
        },
      },
    },
  };
});
