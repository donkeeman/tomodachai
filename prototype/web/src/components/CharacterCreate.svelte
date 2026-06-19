<script lang="ts">
  import { onDestroy } from "svelte";
  import { createOpen, snapshot, toast } from "../lib/store";
  import { initPreview, updatePreview, disposePreview } from "../lib/preview";
  import { spawnCharacter } from "../lib/village";
  import { createCharacter } from "../lib/api";
  import {
    SKIN_TONES, HAIR_COLORS, BODY_COLORS, EYE_COLORS, HAIR_STYLES,
    type AvatarLook, type HairStyle,
  } from "../lib/appearance";
  import type { Character } from "../lib/types";

  const PERSONALITIES = [
    { code: "outgoing_charmer", emoji: "😎", name: "인기쟁이", desc: "사교적이고 매력 넘침" },
    { code: "outgoing_dynamo", emoji: "⚡", name: "에너자이저", desc: "활발하고 적극적" },
    { code: "confident_gogetter", emoji: "🔥", name: "야심가", desc: "자신만만, 목표 지향" },
    { code: "easygoing_softie", emoji: "🍮", name: "순둥이", desc: "느긋하고 다정함" },
    { code: "easygoing_carer", emoji: "🤗", name: "돌봄이", desc: "배려심 많고 따뜻함" },
    { code: "independent_thinker", emoji: "🧠", name: "사색가", desc: "독립적이고 깊이 있음" },
    { code: "independent_introvert", emoji: "🌙", name: "내향러", desc: "조용하고 차분함" },
    { code: "confident_busybee", emoji: "🐝", name: "부지런쟁이", desc: "바지런하고 활동적" },
  ];
  const STEPS = ["기본", "외모", "성격", "완성"];

  let step = 0;
  let name = "";
  let gender: "M" | "F" = "F";
  let skin = SKIN_TONES[0];
  let hairColor = HAIR_COLORS[1];
  let hairStyle: HairStyle = "long";
  let bodyColor = BODY_COLORS[6];
  let eyeColor = EYE_COLORS[0];
  let persona = PERSONALITIES[0].code;
  let habit = "";
  let busy = false;

  $: look = { gender, skin, hairColor, hairStyle, bodyColor, eyeColor } as AvatarLook;
  $: updatePreview(look); // 미리보기 갱신(닫혀 있으면 내부에서 no-op)

  // 캔버스 존재(모달 열림)에 생명주기를 묶는다 — Svelte 반응성 부작용 회피.
  function preview(node: HTMLCanvasElement) {
    initPreview(node, look);
    return { destroy() { disposePreview(); reset(); } };
  }
  onDestroy(disposePreview);

  function reset() {
    step = 0; name = ""; gender = "F";
    skin = SKIN_TONES[0]; hairColor = HAIR_COLORS[1]; hairStyle = "long";
    bodyColor = BODY_COLORS[6]; eyeColor = EYE_COLORS[0];
    persona = PERSONALITIES[0].code; habit = "";
  }
  function close() { createOpen.set(false); }

  function nextId(): number {
    const ids = ($snapshot?.characters ?? []).map((c) => c.id);
    return (ids.length ? Math.max(...ids) : 0) + 1;
  }

  async function finish() {
    if (busy) return;
    busy = true;
    const nm = name.trim() || "이름없음";
    const id = nextId();
    const char: Character = {
      id, name: nm, gender, location: "fountain",
      mood: "평온", hunger: 0, satisfaction: 50,
      lover: null, best_friend: null, enemy: null,
      crushes: [], food_eaten: [], friends: [], dex: [],
    };
    spawnCharacter(char, look); // 즉시 마을 등장(외모 적용)
    try {
      await createCharacter({
        id, name: nm, gender, personality_code: persona,
        speech_habits: habit.trim() ? { normal: habit.trim() } : {},
        favorite_color: bodyColor, appearance: look, location: "fountain",
      });
      toast(`✨ ${nm} 이(가) 마을에 왔어요!`);
    } catch {
      toast(`✨ ${nm} 등장! (서버 저장은 백엔드 연결 후)`);
    }
    busy = false;
    close();
  }
</script>

{#if $createOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="cc-overlay" on:click|self={close}>
    <div class="cc-modal">
      <button class="cc-x" on:click={close} aria-label="닫기">✕</button>

      <div class="cc-preview">
        <canvas use:preview></canvas>
        <div class="cc-namechip">{name.trim() || "새 친구"}</div>
      </div>

      <div class="cc-form">
        <div class="cc-steps">
          {#each STEPS as s, i}
            <button class="cc-dot" class:on={i === step} class:done={i < step} on:click={() => (step = i)}>{s}</button>
          {/each}
        </div>

        {#if step === 0}
          <h3>🐣 어떤 친구를 만들까요?</h3>
          <span class="cc-l">이름</span>
          <input class="cc-input" bind:value={name} maxlength="8" placeholder="이름 (최대 8자)" />
          <span class="cc-l">성별</span>
          <div class="cc-row">
            <button class="cc-pick" class:on={gender === "F"} on:click={() => (gender = "F")}>👧 여자</button>
            <button class="cc-pick" class:on={gender === "M"} on:click={() => (gender = "M")}>👦 남자</button>
          </div>
        {:else if step === 1}
          <h3>🎨 외모를 꾸며요</h3>
          <span class="cc-l">피부톤</span>
          <div class="cc-sw">{#each SKIN_TONES as c}<button class="s" class:on={skin === c} style="background:{c}" on:click={() => (skin = c)} aria-label="피부톤"></button>{/each}</div>
          <span class="cc-l">머리 색</span>
          <div class="cc-sw">{#each HAIR_COLORS as c}<button class="s" class:on={hairColor === c} style="background:{c}" on:click={() => (hairColor = c)} aria-label="머리색"></button>{/each}</div>
          <span class="cc-l">머리 스타일</span>
          <div class="cc-row wrap">{#each HAIR_STYLES as h}<button class="cc-pick sm" class:on={hairStyle === h.id} on:click={() => (hairStyle = h.id)}>{h.label}</button>{/each}</div>
          <span class="cc-l">옷 색</span>
          <div class="cc-sw">{#each BODY_COLORS as c}<button class="s" class:on={bodyColor === c} style="background:{c}" on:click={() => (bodyColor = c)} aria-label="옷색"></button>{/each}</div>
          <span class="cc-l">눈 색</span>
          <div class="cc-sw">{#each EYE_COLORS as c}<button class="s" class:on={eyeColor === c} style="background:{c}" on:click={() => (eyeColor = c)} aria-label="눈색"></button>{/each}</div>
        {:else if step === 2}
          <h3>💭 성격을 골라요</h3>
          <div class="cc-personas">
            {#each PERSONALITIES as p}
              <button class="cc-persona" class:on={persona === p.code} on:click={() => (persona = p.code)}>
                <span class="e">{p.emoji}</span><b>{p.name}</b><small>{p.desc}</small>
              </button>
            {/each}
          </div>
          <span class="cc-l">말버릇 <i class="opt">(선택)</i></span>
          <input class="cc-input" bind:value={habit} maxlength="12" placeholder="예: ~다냥, ~해용" />
        {:else}
          <h3>🎉 완성!</h3>
          <ul class="cc-summary">
            <li><b>{name.trim() || "이름없음"}</b> · {gender === "F" ? "여자" : "남자"}</li>
            <li>성격 · {PERSONALITIES.find((p) => p.code === persona)?.name}</li>
            {#if habit.trim()}<li>말버릇 · “{habit.trim()}”</li>{/if}
          </ul>
          <p class="cc-note">마을에 바로 등장해요. 서버 저장·시뮬 참여는 백엔드 연결 시 적용됩니다.</p>
        {/if}

        <div class="cc-nav">
          {#if step > 0}<button class="cc-ghost" on:click={() => (step -= 1)}>← 이전</button>{/if}
          <div class="cc-grow"></div>
          {#if step < STEPS.length - 1}
            <button class="cc-go" on:click={() => (step += 1)}>다음 →</button>
          {:else}
            <button class="cc-go" disabled={busy} on:click={finish}>🏡 마을에 데려오기</button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .cc-overlay {
    position: fixed; inset: 0; z-index: 50;
    background: rgba(60, 40, 50, 0.42);
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(3px);
  }
  .cc-modal {
    width: min(720px, 94vw); height: min(520px, 92vh);
    display: flex; overflow: hidden;
    background: #fff6ef; border-radius: 24px;
    box-shadow: 0 18px 50px rgba(80, 40, 60, 0.34);
    border: 3px solid #ffe0ea; position: relative;
    font-family: "Apple SD Gothic Neo", system-ui, sans-serif;
  }
  .cc-x {
    position: absolute; top: 12px; right: 14px; z-index: 2;
    width: 32px; height: 32px; border: 0; border-radius: 50%;
    background: #ffd9e8; color: #b5446e; font-weight: 800; cursor: pointer;
  }
  .cc-preview {
    width: 42%; position: relative;
    background: radial-gradient(120% 100% at 50% 18%, #fff0d9 0%, #ffd9ea 64%, #f7b9d6 100%);
    display: flex; align-items: flex-end; justify-content: center;
  }
  .cc-preview canvas { position: absolute; inset: 0; width: 100%; height: 100%; outline: none; }
  .cc-namechip {
    position: relative; margin-bottom: 16px; z-index: 1;
    background: #fff; color: #b5446e; font-weight: 800;
    padding: 5px 16px; border-radius: 999px; box-shadow: 0 3px 10px rgba(120, 60, 90, 0.22);
  }
  .cc-form { flex: 1; padding: 18px 20px 16px; display: flex; flex-direction: column; overflow-y: auto; }
  .cc-steps { display: flex; gap: 6px; margin-bottom: 8px; }
  .cc-dot {
    flex: 1; border: 0; cursor: pointer; font-size: 12px; font-weight: 700;
    padding: 6px 0; border-radius: 999px; background: #f1e3ea; color: #ad8ea0;
  }
  .cc-dot.done { background: #ffe0ea; color: #d2477e; }
  .cc-dot.on { background: #ff7eae; color: #fff; }
  h3 { margin: 8px 0 10px; color: #6b4a5a; font-size: 17px; }
  .cc-l { font-size: 12px; font-weight: 700; color: #b08aa0; margin: 10px 0 5px; display: block; }
  .cc-l .opt { font-style: normal; color: #c9b3c0; font-weight: 600; }
  .cc-input {
    width: 100%; box-sizing: border-box; padding: 10px 12px; font-size: 14px;
    border: 2px solid #ffd9e8; border-radius: 12px; background: #fff; outline: none;
  }
  .cc-input:focus { border-color: #ff7eae; }
  .cc-row { display: flex; gap: 8px; }
  .cc-row.wrap { flex-wrap: wrap; }
  .cc-pick {
    flex: 1; padding: 11px 0; border: 2px solid #ffd9e8; border-radius: 12px;
    background: #fff; color: #7a5a68; font-weight: 700; cursor: pointer; font-size: 14px;
  }
  .cc-pick.sm { flex: 0 0 auto; padding: 9px 14px; font-size: 13px; }
  .cc-pick.on { border-color: #ff7eae; background: #ffeef4; color: #d2477e; }
  .cc-sw { display: flex; flex-wrap: wrap; gap: 7px; }
  .cc-sw .s {
    width: 30px; height: 30px; border-radius: 50%; cursor: pointer;
    border: 3px solid #fff; box-shadow: 0 0 0 1px #e7d3dd; padding: 0;
  }
  .cc-sw .s.on { box-shadow: 0 0 0 3px #ff7eae; transform: scale(1.08); }
  .cc-personas { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .cc-persona {
    display: flex; flex-direction: column; align-items: flex-start; gap: 1px;
    padding: 9px 11px; border: 2px solid #ffd9e8; border-radius: 14px;
    background: #fff; cursor: pointer; text-align: left;
  }
  .cc-persona .e { font-size: 18px; }
  .cc-persona b { color: #6b4a5a; font-size: 13px; }
  .cc-persona small { color: #ab8c9b; font-size: 11px; }
  .cc-persona.on { border-color: #ff7eae; background: #ffeef4; }
  .cc-summary { list-style: none; padding: 0; margin: 4px 0; }
  .cc-summary li { padding: 7px 0; border-bottom: 1px dashed #f0dde6; color: #6b4a5a; }
  .cc-summary b { color: #d2477e; }
  .cc-note { font-size: 12px; color: #ab8c9b; line-height: 1.5; }
  .cc-nav { margin-top: auto; padding-top: 12px; display: flex; align-items: center; gap: 8px; }
  .cc-grow { flex: 1; }
  .cc-ghost { border: 0; background: none; color: #ab8c9b; font-weight: 700; cursor: pointer; }
  .cc-go {
    border: 0; padding: 11px 18px; border-radius: 999px; cursor: pointer;
    background: #ff7eae; color: #fff; font-weight: 800; font-size: 14px;
    box-shadow: 0 4px 12px rgba(255, 126, 174, 0.45);
  }
  .cc-go:disabled { opacity: 0.6; cursor: wait; }
</style>
