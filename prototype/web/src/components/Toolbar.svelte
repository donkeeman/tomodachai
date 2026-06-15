<script lang="ts">
  import { albumOpen, toast } from "../lib/store";
  import { saveGame, resetGame } from "../lib/api";

  async function save() {
    try {
      const out = await saveGame();
      toast(out.error ? "⚠️ " + out.error : out.message);
    } catch { toast("⚠️ 서버 연결 실패"); }
  }
  async function reset() {
    if (!window.confirm("정말 새 마을로 시작할까요? 지금 마을은 사라집니다!")) return;
    try { await resetGame(); location.reload(); } catch { toast("⚠️ 서버 연결 실패"); }
  }
</script>

<div id="toolbar">
  <button on:click={() => albumOpen.update((v) => !v)}>📒 기록</button>
  <button on:click={save}>💾 저장</button>
  <button class="reset" on:click={reset}>🔄 새 마을</button>
</div>
