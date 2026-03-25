import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
import Components from 'unplugin-vue-components/vite'
import AutoImport from 'unplugin-auto-import/vite'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  base: '/lab/pricone-re-synthesis/',
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
    // ローカル SFC コンポーネント + PrimeVue コンポーネントを自動インポート
    Components({
      dirs: ['src/components'],
      resolvers: [PrimeVueResolver()],
      dts: 'src/types/components.d.ts',
    }),
    // Vue API・Pinia・コンポーザブルを自動インポート
    AutoImport({
      imports: ['vue', 'pinia', '@vueuse/core'],
      dirs: ['src/composables', 'src/stores'],
      vueTemplate: true,
      dts: 'src/types/auto-imports.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
  },
  build: {
    minify: 'esbuild',
  },
  // プロダクションビルド時のみconsole.*とdebuggerを除去
  esbuild:
    mode === 'production'
      ? {
          drop: ['console', 'debugger'],
        }
      : {},
}))
