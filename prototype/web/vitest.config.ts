import { defineConfig } from "vitest/config";

// 순수 TS 로직(src/sim, src/llm) 단위 테스트용. Svelte/Babylon 플러그인 없이 node 환경.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
