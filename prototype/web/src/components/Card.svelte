<script lang="ts">
  import { selectedId, cardMode, snapshot, toast } from "../lib/store";
  import { feed, give } from "../lib/api";
  import { pollNow } from "../lib/sim";
  import type { Character } from "../lib/types";

  $: snap = $snapshot;
  $: char = (snap && $selectedId != null ? snap.characters.find((c) => c.id === $selectedId) : null) ?? null;
  $: foods = snap?.foods ?? [];
  $: locNames = snap?.locations ?? {};

  // 선택이 바뀌면 메뉴 모드 초기화
  let prevId: number | null = null;
  $: if ($selectedId !== prevId) { prevId = $selectedId; cardMode.set("info"); }

  const TIER_ORDER: Record<string, number> = { favorite: 0, like: 1, normal: 2, dislike: 3, worst: 4 };
  const TIER_EMOJI: Record<string, string> = { favorite: "💖", like: "🙂", normal: "😐", dislike: "😖", worst: "🤢" };
  const clamp = (v: number) => Math.max(0, Math.min(100, v));
  const satColor = (v: number) => (v < 20 ? "#e57373" : v < 50 ? "#ffb74d" : "#7ec77e");
  const hunColor = (v: number) => (v >= 70 ? "#e57373" : v >= 40 ? "#ffb74d" : "#a5d6a7");
  function dexChips(c: Character) {
    const dex = (c.dex || []).slice().sort((a, b) => TIER_ORDER[a.tier] - TIER_ORDER[b.tier]);
    const chips = dex.map((d) => `${TIER_EMOJI[d.tier]}${d.name}`).join(" ");
    const unknown = foods.length - dex.length;
    if (!dex.length) return `아직 먹여본 음식이 없어요 (???×${unknown})`;
    return chips + (unknown > 0 ? ` · ???×${unknown}` : "");
  }
  async function doFeed(id: number, fid: number) {
    try {
      const out = await feed(id, fid);
      if (out.error) toast("⚠️ " + out.error);
    } catch { toast("⚠️ 서버 연결 실패"); }
    cardMode.set("info");
    pollNow();
  }
  async function doGive(id: number, tool: string) {
    try {
      const out = await give(id, tool);
      if (out.error) toast("⚠️ " + out.error);
      else if (out.messages?.length) toast(out.messages[out.messages.length - 1]);
    } catch { toast("⚠️ 서버 연결 실패"); }
    cardMode.set("info");
    pollNow();
  }
</script>

{#if char}
  <div id="card">
    <div class="cstats">
      <h2>{char.gender === "F" ? "👩" : "👨"} {char.name}</h2>
      <div class="row">
        기분: <b>{char.mood}</b>{#if char.satisfaction < 0} · <b>😱 절망</b>{/if} ·
        <b>{locNames[char.location] || char.location}</b>
      </div>
      <div class="row gauge">
        <span class="glabel">🧡 만족도</span>
        <span class="bar"><i style="width:{clamp(char.satisfaction)}%;background:{satColor(char.satisfaction)}"></i></span>
      </div>
      <div class="row gauge">
        <span class="glabel">🍚 배고픔</span>
        <span class="bar"><i style="width:{clamp(char.hunger)}%;background:{hunColor(char.hunger)}"></i></span>
      </div>
      {#if char.lover}<div class="row">❤️ 연인: {char.lover}</div>
      {:else if char.crushes.length}<div class="row">💘 반함: {char.crushes.join(", ")}</div>{/if}
      {#if char.best_friend}<div class="row">⭐ 베프: {char.best_friend}</div>{/if}
      {#if char.enemy}<div class="row">⚡ 앙숙: {char.enemy}</div>{/if}
      <div class="sect">👥 친구 순위</div>
      {#if char.friends.length}
        {#each char.friends as f, i}<div class="row small">{i + 1}. <b>{f.name}</b> · {f.label}</div>{/each}
      {:else}<div class="row small">아직 만난 주민이 없어요</div>{/if}
      <div class="sect">🍽 좋아하는 음식 (도감)</div>
      <div class="row small">{dexChips(char)}</div>
    </div>
    <div class="cacts">
      {#if $cardMode === "foods"}
        <div class="foods">
          {#each foods as f, i}
            <button class:tried={char.food_eaten[i]} on:click={() => doFeed(char.id, i)}>{f}</button>
          {/each}
          <button class="back" on:click={() => cardMode.set("info")}>← 돌아가기</button>
        </div>
      {:else if $cardMode === "tools"}
        <div class="foods">
          <button class="wide" on:click={() => doGive(char.id, "camera")}>📷 카메라 — 사진 찍어오기</button>
          <button class="wide" on:click={() => doGive(char.id, "frying_pan")}>🍳 프라이팬 — 즉흥 요리</button>
          <button class="back" on:click={() => cardMode.set("info")}>← 돌아가기</button>
        </div>
      {:else}
        <div class="actions">
          <button class="feed" on:click={() => cardMode.set("foods")}>🍙 밥 주기</button>
          <button on:click={() => cardMode.set("tools")}>🎁 도구</button>
        </div>
      {/if}
    </div>
  </div>
{/if}
