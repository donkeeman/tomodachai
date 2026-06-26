<script lang="ts">
  import { albumOpen, createOpen, logOpen, toast } from "../lib/store";
  import { saveGame, resetGame } from "../lib/api";

  async function save() {
    try {
      const out = await saveGame();
      toast(out.error ? out.error : out.message);
    } catch { toast("서버 연결 실패"); }
  }
  async function reset() {
    if (!window.confirm("정말 새 마을로 시작할까요? 지금 마을은 사라집니다!")) return;
    try { await resetGame(); location.reload(); } catch { toast("서버 연결 실패"); }
  }
</script>

<div id="toolbar">
  <button class="make" on:click={() => createOpen.set(true)}>새 친구</button>
  <button on:click={() => logOpen.update((v) => !v)}>소식</button>
  <button on:click={() => albumOpen.update((v) => !v)}>기록</button>
  <button on:click={save}>저장</button>
  <button class="reset" on:click={reset}>새 마을</button>
</div>

<style>
  .make { background: #ff7eae !important; color: #fff !important; font-weight: 800; }
</style>
