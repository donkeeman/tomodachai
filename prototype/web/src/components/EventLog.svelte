<script lang="ts">
  import { onMount } from "svelte";
  import { logItems } from "../lib/store";
  import type { EventItem } from "../lib/types";
  // 반응문 안에서 tick() 을 쓰면 Svelte 5 에서 무한 갱신 루프가 생길 수 있어,
  // 명시적 subscribe + rAF 스크롤로 처리한다.
  let el: HTMLDivElement;
  let items: EventItem[] = [];
  onMount(() => {
    const unsub = logItems.subscribe((v) => {
      items = v;
      requestAnimationFrame(() => { if (el) el.scrollTop = el.scrollHeight; });
    });
    return unsub;
  });
</script>

<div id="log" bind:this={el}>
  <h3>📋 마을 소식</h3>
  {#each items as ev (ev.seq)}
    <div class="ev">
      <span class="time">Day {ev.day} {ev.clock}</span><br />
      {#if ev.scene}<span class="scene">{ev.scene}</span><br />{/if}
      {#each ev.messages as m}<span class="msg">{m}</span><br />{/each}
      {#each ev.dialogue as line}<span class="line"><span class="who">{line[0]}</span> {line[1]}</span><br />{/each}
    </div>
  {/each}
</div>
