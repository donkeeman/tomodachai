<script lang="ts">
  import { snapshot, followName, modelLoaded } from "../lib/store";
</script>

<div id="hud">
  {#if $snapshot}🏘 {$snapshot.village} · Day {$snapshot.day} · {$snapshot.clock}{:else}접속 중...{/if}
  <div class="sub">
    {#if $snapshot}엔진: {$snapshot.provider}{$modelLoaded ? "+glb" : ""}{$snapshot.realtime
      ? " · ⏰ 리얼타임"
      : ""}{$snapshot.asleep ? " · 🌙 자는 시간" : ""}{$followName ? ` · 🎯 ${$followName} 따라가는 중` : ""}{/if}
  </div>
</div>
