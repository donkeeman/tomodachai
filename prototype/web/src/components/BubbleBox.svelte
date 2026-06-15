<script lang="ts">
  import { snapshot, toast } from "../lib/store";
  import { answerBubble } from "../lib/api";
  import { pollNow } from "../lib/sim";

  let busy = false;
  $: confess = ($snapshot?.bubbles ?? [])
    .map((b, i) => ({ ...b, _idx: i }))
    .filter((b) => b.kind === "confess_request");

  async function ans(idx: number, char: string, allow: boolean) {
    if (busy) return;
    busy = true;
    try {
      const out = await answerBubble(idx, char, allow);
      if (out.error) toast("⚠️ " + out.error);
    } catch { toast("⚠️ 서버 연결 실패"); }
    busy = false;
    await pollNow();
  }
</script>

{#if confess.length}
  {@const b = confess[0]}
  <div id="bubblebox">
    <div class="title">💗 말풍선 도착!{confess.length > 1 ? ` (+${confess.length - 1}건 대기)` : ""}</div>
    <div class="text">{b.text || `${b.char}이(가) 할 말이 있어요`}</div>
    <div class="btns">
      <button class="yes" disabled={busy} on:click={() => ans(b._idx, b.char, true)}>
        {busy ? "두근두근..." : "💕 해!"}
      </button>
      <button class="no" disabled={busy} on:click={() => ans(b._idx, b.char, false)}>🙅 그만해</button>
    </div>
  </div>
{/if}
