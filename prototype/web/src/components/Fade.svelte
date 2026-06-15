<script lang="ts">
  import { onMount } from "svelte";
  import { viewMode } from "../lib/store";
  // 공간 전환 시 짧은 로딩 페이드. 명시적 subscribe (반응형 블록의 자기 재실행 방지)
  let on = false;
  onMount(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let first = true;
    const unsub = viewMode.subscribe(() => {
      if (first) { first = false; return; }
      on = true;
      clearTimeout(timer);
      timer = setTimeout(() => { on = false; }, 320);
    });
    return () => { unsub(); clearTimeout(timer); };
  });
</script>

<div id="fade" class:on></div>
