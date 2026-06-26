<script lang="ts">
  import { snapshot, albumOpen } from "../lib/store";
  $: photos = $snapshot?.photos ?? [];
  $: dishes = $snapshot?.dishes ?? [];
</script>

{#if $albumOpen}
  <div id="album">
    <h3>마을 기록</h3>
    {#if photos.length}
      <div class="cat">사진 갤러리</div>
      {#each photos as p}
        <div class="item"><b>{p.title}</b><br /><span class="sub">Day {p.day}, {p.author} 촬영, 피사체 {p.subject || "?"}</span></div>
      {/each}
    {/if}
    {#if dishes.length}
      <div class="cat">요리 카탈로그</div>
      {#each dishes as d}<div class="item"><b>{d.dish}</b> <span class="sub">Day {d.day}, {d.author}</span></div>{/each}
    {/if}
    <button class="closeb" on:click={() => albumOpen.set(false)}>닫기</button>
  </div>
{/if}
