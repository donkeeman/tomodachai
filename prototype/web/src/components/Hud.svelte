<script lang="ts">
  import { snapshot } from "../lib/store";
</script>

<!-- 마을 이름표 — 마을 이름만. 일자/시간/엔진 등은 노출하지 않음(N일차는 추후 저장 화면에서). -->
<div id="hud">
  {#if $snapshot}{$snapshot.village}{:else}접속 중...{/if}
</div>
