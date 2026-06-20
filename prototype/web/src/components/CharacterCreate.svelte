<script lang="ts">
  import { onDestroy } from "svelte";
  import { createOpen, snapshot, toast } from "../lib/store";
  import { initPreview, updatePreview, disposePreview, playMotion } from "../lib/preview";
  import { spawnCharacter } from "../lib/village";
  import { createCharacter } from "../lib/api";
  import {
    SKIN_TONES, HAIR_COLORS, BODY_COLORS, EYE_COLORS, HAIR_STYLES,
    type AvatarLook, type HairStyle,
  } from "../lib/appearance";
  import {
    TRAITS, DEFAULT_TRAITS, SCALE_MIN, SCALE_MAX, determinePersonality,
    personalityLabel, personalityDesc, toBackendSliders, type TraitValues,
  } from "../lib/personality";
  import type { Character } from "../lib/types";

  const STEPS = ["기본", "외모", "목소리", "성격", "완성"];
  const SCALE = Array.from({ length: SCALE_MAX - SCALE_MIN + 1 }, (_, i) => SCALE_MIN + i); // [1..8]
  const APP_TABS = ["피부", "머리", "이목구비", "옷"]; // 외모 하위 분류
  let appTab = 0;
  const VOICE_PRESETS = [
    { id: "female", label: "여성 목소리" },
    { id: "male", label: "남성 목소리" },
  ];

  let step = 0;
  // 기본 프로필
  let name = "";
  let gender: "M" | "F" = "F";
  let favColor = BODY_COLORS[6];        // 좋아하는 색 = 기본 옷 색
  let birthMonth: number | null = null; // 1~12 (선택)
  let birthDay: number | null = null;   // 1~31 (선택)
  let age: number | null = null;        // 선택(프론트 표기용 — 백엔드 미저장)
  // 외모
  let skin = SKIN_TONES[0];
  let hairColor = HAIR_COLORS[1];
  let hairStyle: HairStyle = "long";
  let bodyColor = favColor;        // 좋아하는 색에서 기본값, 이후 개별 변경 가능
  let bodyTouched = false;         // 옷 색을 직접 바꿨는지
  let eyeColor = EYE_COLORS[0];
  // 목소리
  let voicePreset = "female";
  let pitch = 4;                   // 1~8
  let speed = 4;                   // 1~8
  // 성격(트레잇 1~8)
  let traits: TraitValues = { ...DEFAULT_TRAITS };
  let busy = false;
  let revealed = false; // 완성 버튼 이후 성격을 공개하는 리빌 화면

  // 좋아하는 색이 바뀌면(아직 옷 색을 직접 만지지 않았다면) 기본 옷 색도 따라간다.
  function pickFav(c: string) {
    favColor = c;
    if (!bodyTouched) bodyColor = c;
  }
  function pickBody(c: string) { bodyColor = c; bodyTouched = true; }
  // 성별을 바꾸면 음성 프리셋 기본값도 맞춘다(직접 고르기 전까지).
  let voiceTouched = false;
  function pickGender(g: "M" | "F") {
    gender = g;
    if (!voiceTouched) voicePreset = g === "F" ? "female" : "male";
  }

  $: persona = determinePersonality(traits);
  $: look = { gender, skin, hairColor, hairStyle, bodyColor, eyeColor } as AvatarLook;
  $: updatePreview(look); // 미리보기 갱신(닫혀 있으면 내부에서 no-op)

  // 캔버스 존재(뷰 열림)에 생명주기를 묶는다 — Svelte 반응성 부작용 회피.
  function preview(node: HTMLCanvasElement) {
    initPreview(node, look);
    return { destroy() { disposePreview(); reset(); } };
  }
  onDestroy(disposePreview);

  function reset() {
    step = 0; appTab = 0; revealed = false; name = ""; gender = "F";
    favColor = BODY_COLORS[6]; birthMonth = null; birthDay = null; age = null;
    skin = SKIN_TONES[0]; hairColor = HAIR_COLORS[1]; hairStyle = "long";
    bodyColor = favColor; bodyTouched = false; eyeColor = EYE_COLORS[0];
    voicePreset = "female"; pitch = 4; speed = 4; voiceTouched = false;
    traits = { ...DEFAULT_TRAITS };
  }
  function close() { createOpen.set(false); }

  function nextId(): number {
    const ids = ($snapshot?.characters ?? []).map((c) => c.id);
    return (ids.length ? Math.max(...ids) : 0) + 1;
  }

  // "MM-DD" 또는 빈 문자열
  function birthdayStr(): string {
    if (!birthMonth || !birthDay) return "";
    return `${String(birthMonth).padStart(2, "0")}-${String(birthDay).padStart(2, "0")}`;
  }
  // 1~8 → 백엔드 0~10
  const to10 = (v: number) => Math.round(((v - 1) / 7) * 10);

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
        personality: toBackendSliders(traits),
        speech_habits: {}, // 말버릇은 생성에서 제외 — 추후 고민/레벨업 보상으로 세부 지정
        favorite_color: favColor, birthday: birthdayStr(),
        voice: { preset: voicePreset, pitch: to10(pitch), speed: to10(speed) },
        appearance: look, location: "fountain",
      });
      toast(`${nm} 이(가) 마을에 왔어요!`);
    } catch {
      toast(`${nm} 등장! (서버 저장은 백엔드 연결 후)`);
    }
    busy = false;
    revealed = true; // 완성 이후 성격 공개
    playMotion();    // 주민이 신나게 콩콩 뛰는 모션
  }
</script>

{#if $createOpen}
  <div class="cc-view">
    <div class="cc-modal">
      <button class="cc-x" on:click={close}>← 마을로</button>

      <div class="cc-preview">
        <canvas use:preview></canvas>
        <div class="cc-namechip">{name.trim() || "새 친구"}</div>
      </div>

      <div class="cc-form">
        {#if revealed}
          <div class="cc-reveal">
            <h3>완성!</h3>
            <div class="cc-result"><b>{personalityLabel(persona)}</b></div>
            <p class="cc-desc">{personalityDesc(persona)}</p>
            <button class="cc-go" on:click={close}>마을로 가기</button>
          </div>
        {:else}
        <div class="cc-steps">
          {#each STEPS as s, i}
            <button class="cc-dot" class:on={i === step} class:done={i < step} on:click={() => (step = i)}>{s}</button>
          {/each}
        </div>

        {#if step === 0}
          <h3>어떤 친구를 만들까요?</h3>
          <span class="cc-l">이름</span>
          <input class="cc-input" bind:value={name} maxlength="8" placeholder="이름 (최대 8자)" />
          <span class="cc-l">성별</span>
          <div class="cc-row">
            <button class="cc-pick" class:on={gender === "F"} on:click={() => pickGender("F")}>여자</button>
            <button class="cc-pick" class:on={gender === "M"} on:click={() => pickGender("M")}>남자</button>
          </div>
          <span class="cc-l">좋아하는 색 <i class="opt">(기본 옷 색이 돼요)</i></span>
          <div class="cc-sw">{#each BODY_COLORS as c}<button class="s" class:on={favColor === c} style="background:{c}" on:click={() => pickFav(c)} aria-label="좋아하는 색"></button>{/each}</div>
          <span class="cc-l">생일 <i class="opt">(선택)</i></span>
          <div class="cc-row">
            <input class="cc-input" type="number" min="1" max="12" bind:value={birthMonth} placeholder="월" />
            <input class="cc-input" type="number" min="1" max="31" bind:value={birthDay} placeholder="일" />
          </div>
          <span class="cc-l">나이 <i class="opt">(선택)</i></span>
          <input class="cc-input" type="number" min="0" max="999" bind:value={age} placeholder="나이" />
        {:else if step === 1}
          <h3>외모를 꾸며요</h3>
          <div class="cc-subtabs">
            {#each APP_TABS as t, i}
              <button class="cc-subtab" class:on={appTab === i} on:click={() => (appTab = i)}>{t}</button>
            {/each}
          </div>

          {#if appTab === 0}
            <span class="cc-l">피부톤</span>
            <div class="cc-sw">{#each SKIN_TONES as c}<button class="s" class:on={skin === c} style="background:{c}" on:click={() => (skin = c)} aria-label="피부톤"></button>{/each}</div>
          {:else if appTab === 1}
            <span class="cc-l">머리 색</span>
            <div class="cc-sw">{#each HAIR_COLORS as c}<button class="s" class:on={hairColor === c} style="background:{c}" on:click={() => (hairColor = c)} aria-label="머리색"></button>{/each}</div>
            <span class="cc-l">머리 스타일</span>
            <div class="cc-row wrap">{#each HAIR_STYLES as h}<button class="cc-pick sm" class:on={hairStyle === h.id} on:click={() => (hairStyle = h.id)}>{h.label}</button>{/each}</div>
          {:else if appTab === 2}
            <span class="cc-l">눈 색</span>
            <div class="cc-sw">{#each EYE_COLORS as c}<button class="s" class:on={eyeColor === c} style="background:{c}" on:click={() => (eyeColor = c)} aria-label="눈색"></button>{/each}</div>
          {:else}
            <span class="cc-l">옷 색 <i class="opt">(좋아하는 색이 기본값)</i></span>
            <div class="cc-sw">{#each BODY_COLORS as c}<button class="s" class:on={bodyColor === c} style="background:{c}" on:click={() => pickBody(c)} aria-label="옷색"></button>{/each}</div>
          {/if}
        {:else if step === 2}
          <h3>목소리를 정해요</h3>
          <span class="cc-l">목소리 종류</span>
          <div class="cc-row">
            {#each VOICE_PRESETS as v}
              <button class="cc-pick" class:on={voicePreset === v.id} on:click={() => { voicePreset = v.id; voiceTouched = true; }}>{v.label}</button>
            {/each}
          </div>
          <div class="cc-slider">
            <div class="cc-srow"><span class="cc-l">음 높이</span><span class="cc-poles">낮게 ↔ 높게</span></div>
            <input type="range" min="1" max="8" step="1" bind:value={pitch} />
          </div>
          <div class="cc-slider">
            <div class="cc-srow"><span class="cc-l">말 속도</span><span class="cc-poles">느리게 ↔ 빠르게</span></div>
            <input type="range" min="1" max="8" step="1" bind:value={speed} />
          </div>
        {:else if step === 3}
          <h3>성격을 정해요</h3>
          <div class="cc-traits">
            {#each TRAITS as t}
              <div class="cc-trait">
                <div class="cc-srow"><span class="cc-l">{t.label}</span><span class="cc-poles">{t.low} ↔ {t.high}</span></div>
                <div class="cc-scale">
                  {#each SCALE as n}
                    <button
                      class="cc-num"
                      class:on={traits[t.axis] === n}
                      on:click={() => (traits = { ...traits, [t.axis]: n })}
                    >{n}</button>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <h3>완성!</h3>
          <ul class="cc-summary">
            <li><b>{name.trim() || "이름없음"}</b> · {gender === "F" ? "여자" : "남자"}</li>
            {#if birthdayStr()}<li>생일 · {birthdayStr()}</li>{/if}
            {#if age}<li>나이 · {age}</li>{/if}
            <li>목소리 · {VOICE_PRESETS.find((v) => v.id === voicePreset)?.label}</li>
          </ul>
        {/if}

        <div class="cc-nav">
          {#if step > 0}<button class="cc-ghost" on:click={() => (step -= 1)}>← 이전</button>{/if}
          <div class="cc-grow"></div>
          {#if step < STEPS.length - 1}
            <button class="cc-go" on:click={() => (step += 1)}>다음 →</button>
          {:else}
            <button class="cc-go" disabled={busy} on:click={finish}>마을에 데려오기</button>
          {/if}
        </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  /* 민트·연둣빛 테마 */
  .cc-view {
    --pt: #5ec8a0; --pt-d: #2f8f6e; --pt-l: #c8f0dd; --pt-bg: #eafaf2;
    --cream: #f2fbf7; --ink: #355247; --muted: #7aa392;
    position: fixed; inset: 0; z-index: 50;
    background: var(--cream);
    display: flex; align-items: stretch; justify-content: stretch;
  }
  .cc-modal {
    flex: 1; display: flex; overflow: hidden;
    background: var(--cream); position: relative;
    font-family: "Pretendard", "Apple SD Gothic Neo", system-ui, sans-serif;
  }
  .cc-x {
    position: absolute; top: 16px; left: 18px; z-index: 2;
    height: 34px; padding: 0 14px; border: 0; border-radius: 999px;
    background: rgba(255, 255, 255, 0.85); color: var(--pt-d);
    font-weight: 800; font-size: 13px; cursor: pointer;
    box-shadow: 0 2px 8px rgba(40, 110, 85, 0.18);
  }
  .cc-preview {
    width: 46%; position: relative;
    background: radial-gradient(120% 100% at 50% 22%, #f0fbf5 0%, #c8f0dd 60%, #9fe3c4 100%);
    display: flex; align-items: flex-end; justify-content: center;
  }
  .cc-preview canvas { position: absolute; inset: 0; width: 100%; height: 100%; outline: none; }
  .cc-namechip {
    position: relative; margin-bottom: 16px; z-index: 1;
    background: #fff; color: var(--pt-d); font-weight: 800;
    padding: 5px 16px; border-radius: 999px; box-shadow: 0 3px 10px rgba(40, 110, 85, 0.22);
  }
  .cc-form {
    flex: 1; padding: 48px 7% 28px; display: flex; flex-direction: column;
    overflow-y: auto; max-width: 540px; margin: 0 auto; width: 100%; box-sizing: border-box;
  }
  .cc-steps { display: flex; gap: 6px; margin-bottom: 8px; }
  .cc-dot {
    flex: 1; border: 0; cursor: pointer; font-size: 12px; font-weight: 700;
    padding: 6px 0; border-radius: 999px; background: #e4efea; color: #8aa89b;
  }
  .cc-dot.done { background: var(--pt-l); color: var(--pt-d); }
  .cc-dot.on { background: var(--pt); color: #fff; }
  h3 { margin: 8px 0 10px; color: var(--ink); font-size: 17px; }
  .cc-l { font-size: 12px; font-weight: 700; color: var(--muted); margin: 10px 0 5px; display: block; }
  .cc-l .opt { font-style: normal; color: #a9c4ba; font-weight: 600; }
  .cc-input {
    width: 100%; box-sizing: border-box; padding: 10px 12px; font-size: 14px;
    border: 2px solid var(--pt-l); border-radius: 12px; background: #fff; outline: none;
  }
  .cc-input:focus { border-color: var(--pt); }
  .cc-row { display: flex; gap: 8px; }
  .cc-row.wrap { flex-wrap: wrap; }
  .cc-pick {
    flex: 1; padding: 11px 0; border: 2px solid var(--pt-l); border-radius: 12px;
    background: #fff; color: #4f7d6c; font-weight: 700; cursor: pointer; font-size: 14px;
  }
  .cc-pick.sm { flex: 0 0 auto; padding: 9px 14px; font-size: 13px; }
  .cc-pick.on { border-color: var(--pt); background: var(--pt-bg); color: var(--pt-d); }
  .cc-sw { display: flex; flex-wrap: wrap; gap: 7px; }
  .cc-sw .s {
    width: 30px; height: 30px; border-radius: 50%; cursor: pointer;
    border: 3px solid #fff; box-shadow: 0 0 0 1px #d2e8df; padding: 0;
  }
  .cc-sw .s.on { box-shadow: 0 0 0 3px var(--pt); transform: scale(1.08); }
  /* 외모 하위 탭 */
  .cc-subtabs { display: flex; gap: 6px; margin: 4px 0 6px; }
  .cc-subtab {
    flex: 1; border: 2px solid var(--pt-l); border-radius: 999px; background: #fff;
    padding: 7px 0; font-size: 12.5px; font-weight: 700; color: #4f7d6c; cursor: pointer;
  }
  .cc-subtab.on { border-color: var(--pt); background: var(--pt-bg); color: var(--pt-d); }
  /* 음성 슬라이더 */
  .cc-slider { margin: 6px 0 2px; }
  .cc-srow { display: flex; align-items: baseline; justify-content: space-between; }
  .cc-poles { font-size: 11px; color: var(--muted); font-weight: 600; }
  .cc-slider input[type="range"] { width: 100%; accent-color: var(--pt); cursor: pointer; }
  /* 성격 1~8 버튼 스케일 */
  .cc-traits { display: flex; flex-direction: column; gap: 8px; }
  .cc-trait { display: flex; flex-direction: column; }
  .cc-scale { display: flex; gap: 5px; }
  .cc-num {
    flex: 1; aspect-ratio: 1 / 1; min-width: 0; padding: 0;
    border: 2px solid var(--pt-l); border-radius: 10px; background: #fff;
    color: #4f7d6c; font-weight: 700; font-size: 13px; cursor: pointer;
  }
  .cc-num.on { border-color: var(--pt); background: var(--pt); color: #fff; }
  .cc-result {
    margin: 12px 0 2px; padding: 8px 12px; border-radius: 12px;
    background: var(--pt-bg); color: #4f7d6c; font-size: 13px; text-align: center;
  }
  .cc-result b { color: var(--pt-d); }
  /* 완성 이후 성격 공개 화면 */
  .cc-reveal {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 18px; text-align: center;
  }
  .cc-reveal .cc-result { font-size: 18px; line-height: 1.7; padding: 18px 24px; }
  .cc-reveal .cc-result b { font-size: 24px; }
  .cc-desc {
    max-width: 320px; margin: -4px 0 2px; color: var(--ink);
    font-size: 14px; line-height: 1.6;
  }
  .cc-summary { list-style: none; padding: 0; margin: 4px 0; }
  .cc-summary li { padding: 7px 0; border-bottom: 1px dashed #dcefe6; color: var(--ink); }
  .cc-summary b { color: var(--pt-d); }
  .cc-nav { margin-top: auto; padding-top: 12px; display: flex; align-items: center; gap: 8px; }
  .cc-grow { flex: 1; }
  .cc-ghost { border: 0; background: none; color: var(--muted); font-weight: 700; cursor: pointer; }
  .cc-go {
    border: 0; padding: 11px 18px; border-radius: 999px; cursor: pointer;
    background: var(--pt); color: #fff; font-weight: 800; font-size: 14px;
    box-shadow: 0 4px 12px rgba(94, 200, 160, 0.45);
  }
  .cc-go:disabled { opacity: 0.6; cursor: wait; }
</style>
