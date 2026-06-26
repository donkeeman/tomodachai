<script lang="ts">
  import { snapshot, boardOpen } from "../lib/store";
  $: r = $snapshot?.rankings ?? null;
</script>

{#if $boardOpen && r}
  <div id="rankboard">
    <h3>마을 랭킹보드</h3>
    {#each [["베스트 커플", r.best_couple], ["인기 많은 남자", r.popular_m], ["인기 많은 여자", r.popular_f], ["앙숙 매치", r.fighters]] as section}
      {#if (section[1] as string[]).length}
        <div class="cat">{section[0]}</div>
        {#each section[1] as item, i}<div class="item">{i + 1}. {item}</div>{/each}
      {/if}
    {/each}
    <button class="closeb" on:click={() => boardOpen.set(false)}>닫기</button>
  </div>
{/if}
