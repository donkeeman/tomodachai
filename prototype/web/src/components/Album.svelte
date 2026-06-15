<script lang="ts">
  import { snapshot, albumOpen } from "../lib/store";
  $: photos = $snapshot?.photos ?? [];
  $: dishes = $snapshot?.dishes ?? [];
</script>

{#if $albumOpen}
  <div id="album">
    <h3>📒 마을 기록</h3>
    <div class="cat">🖼 사진 갤러리</div>
    {#if photos.length}
      {#each photos as p}
        <div class="item">🖼 <b>{p.title}</b><br /><span class="sub">Day {p.day} · {p.author} 촬영 · 피사체: {p.subject || "?"}</span></div>
      {/each}
    {:else}<div class="item empty">아직 사진이 없어요 — 주민에게 📷 카메라를 줘 보세요</div>{/if}
    <div class="cat">🍳 요리 카탈로그</div>
    {#if dishes.length}
      {#each dishes as d}<div class="item">🍳 <b>{d.dish}</b> <span class="sub">Day {d.day} · {d.author}</span></div>{/each}
    {:else}<div class="item empty">아직 요리가 없어요 — 🍳 프라이팬을 줘 보세요</div>{/if}
    <button class="closeb" on:click={() => albumOpen.set(false)}>닫기</button>
  </div>
{/if}
