<script lang="ts">
  import { selectedId, cardMode, snapshot, toast } from "../lib/store";
  import { feed, give } from "../lib/api";
  import { pollNow } from "../lib/sim";
  import type { Character } from "../lib/types";

  $: snap = $snapshot;
  $: char = (snap && $selectedId != null ? snap.characters.find((c) => c.id === $selectedId) : null) ?? null;
  $: foods = snap?.foods ?? [];

  // 선택이 바뀌면 메뉴 모드 초기화
  let prevId: number | null = null;
  $: if ($selectedId !== prevId) { prevId = $selectedId; cardMode.set("info"); }

  // mood(0~10 구조체) → 표시 라벨. happiness 중심으로 압축하되 stress 가 높으면 우선 반영.
  function moodLabel(m: Character["mood"]): string {
    if (m.stress >= 7) return "예민";
    if (m.happiness >= 7) return "좋음";
    if (m.happiness >= 4) return "보통";
    return "시무룩";
  }
  const clamp = (v: number) => Math.max(0, Math.min(100, v));
  const satColor = (v: number) => (v < 20 ? "#e57373" : v < 50 ? "#ffb74d" : "#7ec77e");
  const hunColor = (v: number) => (v >= 70 ? "#e57373" : v >= 40 ? "#ffb74d" : "#a5d6a7");
  // 도감은 전체 나열 대신 요약 — 진행도(먹여본 수/전체)와 최애만. (foods 있을 때만 호출됨)
  function dexSummary(c: Character) {
    const dex = c.dex || [];
    const progress = `먹여본 음식 ${dex.length}/${foods.length}`;
    const faves = dex.filter((d) => d.tier === "favorite").map((d) => d.name);
    return faves.length ? `${progress} (최애 ${faves.join(", ")})` : progress;
  }
  async function doFeed(id: number, fid: number) {
    try {
      const out = await feed(id, fid);
      if (out.error) toast(out.error);
    } catch { toast("서버 연결 실패"); }
    cardMode.set("info");
    pollNow();
  }
  async function doGive(id: number, tool: string) {
    try {
      const out = await give(id, tool);
      if (out.error) toast(out.error);
      else if (out.messages?.length) toast(out.messages[out.messages.length - 1]);
    } catch { toast("서버 연결 실패"); }
    cardMode.set("info");
    pollNow();
  }
</script>

{#if char}
  <div id="card">
    <div class="cstats">
      <h2>{char.name}</h2>
      <div class="row">
        기분 <b>{moodLabel(char.mood)}</b>{#if char.satisfaction < 0} <b>절망</b>{/if}
      </div>
      <div class="row gauge">
        <span class="glabel">만족도</span>
        <span class="bar"><i style="width:{clamp(char.satisfaction)}%;background:{satColor(char.satisfaction)}"></i></span>
      </div>
      <div class="row gauge">
        <span class="glabel">배고픔</span>
        <span class="bar"><i style="width:{clamp(char.hunger)}%;background:{hunColor(char.hunger)}"></i></span>
      </div>
      {#if char.lover}<div class="row">연인: {char.lover}</div>
      {:else if char.crushes.length}<div class="row">반함: {char.crushes.join(", ")}</div>{/if}
      {#if char.best_friend}<div class="row">베프: {char.best_friend}</div>{/if}
      {#if char.enemy}<div class="row">앙숙: {char.enemy}</div>{/if}
      {#if char.friends.length}
        <div class="sect">친구 순위</div>
        {#each char.friends as f, i}<div class="row small">{i + 1}. <b>{f.name}</b> {f.label}</div>{/each}
      {/if}
      {#if foods.length}
        <div class="sect">음식 도감</div>
        <div class="row small">{dexSummary(char)}</div>
      {/if}
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
          <button class="wide" on:click={() => doGive(char.id, "camera")}>카메라</button>
          <button class="wide" on:click={() => doGive(char.id, "frying_pan")}>프라이팬</button>
          <button class="back" on:click={() => cardMode.set("info")}>← 돌아가기</button>
        </div>
      {:else}
        <div class="actions">
          <button class="feed" on:click={() => cardMode.set("foods")}>밥 주기</button>
          <button on:click={() => cardMode.set("tools")}>도구</button>
        </div>
      {/if}
    </div>
  </div>
{/if}
