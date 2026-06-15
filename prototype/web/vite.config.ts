import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// dev: Vite(1420)가 프론트를, /api 는 파이썬 서버(8765)로 프록시.
// build: dist/ 정적 산출물 → 파이썬/Tauri 가 서빙.
export default defineConfig({
  plugins: [svelte()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8765", changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    target: "esnext",
    sourcemap: false,
    chunkSizeWarningLimit: 4000,
  },
});
