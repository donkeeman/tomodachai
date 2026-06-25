<script lang="ts">
  import { viewMode, roomName } from "../lib/store";
  import { setView } from "../lib/village";
</script>

{#if $viewMode !== "village"}
  <button id="exitbtn" on:click={() => setView("village")}
    >🏡 마을로 나가기{#if $viewMode === "room" && $roomName} · {$roomName}의 방{/if}</button>
{/if}
