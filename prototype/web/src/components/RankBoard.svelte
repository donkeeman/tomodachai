<script lang="ts">
  import { snapshot, boardOpen } from "../lib/store";
  $: r = $snapshot?.rankings ?? null;
  $: empty = !r || !((r.best_couple?.length) || (r.popular_m?.length) || (r.popular_f?.length) || (r.fighters?.length));
</script>

{#if $boardOpen && r}
  <div id="rankboard">
    <h3>마을 랭킹보드</h3>
    {#if empty}
      <div class="item empty" style="text-align:center">마을이 아직 어려요!<br />반함·커플·싸움이 쌓이면 채워집니다.</div>
    {/if}
    {#each [["베스트 커플", r.best_couple], ["인기 많은 남자", r.popular_m], ["인기 많은 여자", r.popular_f], ["앙숙 매치", r.fighters]] as section}
      <div class="cat">{section[0]}</div>
      {#if (section[1] as string[]).length}
        {#each section[1] as item, i}<div class="item">{i + 1}. {item}</div>{/each}
      {:else}<div class="item empty">아직 없음</div>{/if}
    {/each}
    <button class="closeb" on:click={() => boardOpen.set(false)}>닫기</button>
  </div>
{/if}
