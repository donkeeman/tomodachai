<script lang="ts">
  import { viewMode } from "../lib/store";
  import { setView } from "../lib/village";
</script>

{#if $viewMode === "interior"}
  <button id="exitbtn" on:click={() => setView("village")}>🏡 마을로 나가기</button>
{/if}
