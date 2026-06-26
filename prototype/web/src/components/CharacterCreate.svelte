<script lang="ts">
  import { onDestroy } from "svelte";
  import { createOpen, snapshot, toast } from "../lib/store";
  import { initPreview, updatePreview, disposePreview, playMotion } from "../lib/preview";
  import { spawnCharacter } from "../lib/village";
  import { createCharacter } from "../lib/api";
  import {
    SKIN_TONES, HAIR_COLORS, BODY_COLORS, EYE_COLORS, HAIR_STYLES,
    EYE_SHAPES, MOUTH_SHAPES,
    type AvatarLook, type HairStyle, type EyeShape, type MouthShape,
  } from "../lib/appearance";
  import { getHairThumbs } from "../lib/hairThumbs";
  import {
    TRAITS, DEFAULT_TRAITS, SCALE_MIN, SCALE_MAX, determinePersonality,
    personalityLabel, personalityDesc, toBackendSliders, type TraitValues,
  } from "../lib/personality";
  import type { Character } from "../lib/types";

  // 인라인 SVG 아이콘 — 텍스트 화살표(→/←/+/-) 대신. currentColor 상속.
  const SVG = 'width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"';
  const ICON_LEFT = `<svg ${SVG}><path d="M15 6l-6 6 6 6"/></svg>`;
  const ICON_RIGHT = `<svg ${SVG}><path d="M9 6l6 6-6 6"/></svg>`;
  const ICON_PLUS = `<svg ${SVG}><path d="M12 5v14M5 12h14"/></svg>`;
  const ICON_MINUS = `<svg ${SVG}><path d="M5 12h14"/></svg>`;

  const STEPS = ["기본", "외모", "목소리", "성격", "완성"];
  const SCALE = Array.from({ length: SCALE_MAX - SCALE_MIN + 1 }, (_, i) => SCALE_MIN + i); // [1..8]
  const APP_TABS = ["피부", "머리", "이목구비"]; // 외모 하위 분류 (옷=좋아하는 색이라 별도 탭 없음)
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
  let eyeColor = EYE_COLORS[0];
  let eyeShape: EyeShape = "round";
  let eyeSize = 4;                 // 1~8 (figures 배율로 변환)
  let mouthShape: MouthShape = "smile";
  let mouthSize = 4;               // 1~8

  // 헤어 스타일 썸네일(오프스크린 렌더, 1회 생성 후 캐시).
  let hairThumbs: Record<HairStyle, string> = {} as Record<HairStyle, string>;
  getHairThumbs().then((t) => (hairThumbs = t));
  // 목소리
  let voicePreset = "female";
  let pitch = 4;                   // 1~8
  let speed = 4;                   // 1~8
  // 성격(트레잇 1~8)
  let traits: TraitValues = { ...DEFAULT_TRAITS };
  let busy = false;
  let revealed = false; // 완성 버튼 이후 성격을 공개하는 리빌 화면

  // 좋아하는 색 = 아바타 몸통(옷) 색. 단일 입력.
  function pickFav(c: string) { favColor = c; }
  // 성별을 바꾸면 음성 프리셋 기본값도 맞춘다(직접 고르기 전까지).
  let voiceTouched = false;
  function pickGender(g: "M" | "F") {
    gender = g;
    if (!voiceTouched) voicePreset = g === "F" ? "female" : "male";
  }

  // 1~8 → 0.8~1.3 배율(이목구비 크기).
  const sizeMul = (v: number) => 0.8 + ((v - 1) / 7) * 0.5;

  // 생일/나이 ± 스테퍼 — 텍스트 입력칸 대신. null(미설정)에서 첫 조작 시 범위 안으로 들어옴.
  const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
  const stepVal = (cur: number | null, d: number, lo: number, hi: number) => clamp((cur ?? 0) + d, lo, hi);

  $: nameOk = name.trim().length > 0; // 이름은 필수 — 비면 다음/완성 불가
  $: persona = determinePersonality(traits);
  $: look = {
    gender, skin, hairColor, hairStyle, bodyColor: favColor, eyeColor,
    eyeShape, eyeSize: sizeMul(eyeSize),
    mouthShape, mouthSize: sizeMul(mouthSize),
  } as AvatarLook;
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
    eyeColor = EYE_COLORS[0];
    eyeShape = "round"; eyeSize = 4; mouthShape = "smile"; mouthSize = 4;
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
      mood: { happiness: 5, energy: 5, stress: 2 }, hunger: 0, satisfaction: 50,
      lover: null, best_friend: null, enemy: null,
      crushes: [], food_eaten: [], friends: [], dex: [], look,
    };
    spawnCharacter(char, look, persona); // 즉시 마을 등장(외모 + 성격 모션 적용)
    try {
      await createCharacter({
        id, name: nm, gender, personality_code: persona,
        personality: toBackendSliders(traits),
        speech_habits: {}, // 말버릇은 생성에서 제외 — 추후 고민/레벨업 보상으로 세부 지정
        favorite_color: favColor, birthday: birthdayStr(),
        voice: { preset: voicePreset, pitch: to10(pitch), speed: to10(speed) },
        appearance: look, location: "fountain",
      });
      toast(`${nm} 마을 도착!`);
    } catch {
      toast(`${nm} 마을 도착!`); // 서버 저장 실패해도 로컬 등장은 유지 — 플레이어에겐 동일하게
    }
    busy = false;
    revealed = true; // 완성 이후 성격 공개
    playMotion();    // 주민이 신나게 콩콩 뛰는 모션
  }
</script>

{#if $createOpen}
  <div class="cc-view">
    <div class="cc-modal">
      <button class="cc-x" on:click={close}><span class="cc-ic">{@html ICON_LEFT}</span>마을로</button>

      <div class="cc-preview">
        <canvas use:preview></canvas>
        {#if name.trim()}<div class="cc-namechip">{name.trim()}</div>{/if}
      </div>

      <div class="cc-form">
        <div class="cc-card">
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
          <input class="cc-name" bind:value={name} maxlength="8" placeholder="이름을 지어 주세요" />
          <span class="cc-l">성별</span>
          <div class="cc-row">
            <button class="cc-pick" class:on={gender === "F"} on:click={() => pickGender("F")}>여자</button>
            <button class="cc-pick" class:on={gender === "M"} on:click={() => pickGender("M")}>남자</button>
          </div>
          <span class="cc-l">좋아하는 색</span>
          <div class="cc-sw">{#each BODY_COLORS as c}<button class="s" class:on={favColor === c} style="background:{c}" on:click={() => pickFav(c)} aria-label="좋아하는 색"></button>{/each}</div>
          <span class="cc-l">생일 <i class="opt">선택</i></span>
          <div class="cc-row">
            <div class="cc-step">
              <button class="cc-stepb" on:click={() => (birthMonth = stepVal(birthMonth, -1, 1, 12))} aria-label="월 감소">{@html ICON_MINUS}</button>
              <span class="cc-stepv">{birthMonth ?? "-"}<i>월</i></span>
              <button class="cc-stepb" on:click={() => (birthMonth = stepVal(birthMonth, 1, 1, 12))} aria-label="월 증가">{@html ICON_PLUS}</button>
            </div>
            <div class="cc-step">
              <button class="cc-stepb" on:click={() => (birthDay = stepVal(birthDay, -1, 1, 31))} aria-label="일 감소">{@html ICON_MINUS}</button>
              <span class="cc-stepv">{birthDay ?? "-"}<i>일</i></span>
              <button class="cc-stepb" on:click={() => (birthDay = stepVal(birthDay, 1, 1, 31))} aria-label="일 증가">{@html ICON_PLUS}</button>
            </div>
          </div>
          <span class="cc-l">나이 <i class="opt">선택</i></span>
          <div class="cc-step">
            <button class="cc-stepb" on:click={() => (age = stepVal(age, -1, 0, 120))} aria-label="나이 감소">{@html ICON_MINUS}</button>
            <span class="cc-stepv">{age ?? "-"}<i>살</i></span>
            <button class="cc-stepb" on:click={() => (age = stepVal(age, 1, 0, 120))} aria-label="나이 증가">{@html ICON_PLUS}</button>
          </div>
        {:else if step === 1}
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
            <div class="cc-row wrap">{#each HAIR_STYLES as h}
              <button class="cc-hair" class:on={hairStyle === h.id} on:click={() => (hairStyle = h.id)} title={h.label}>
                {#if hairThumbs[h.id]}<img src={hairThumbs[h.id]} alt={h.label} />{/if}
                <span>{h.label}</span>
              </button>
            {/each}</div>
          {:else if appTab === 2}
            <span class="cc-l">눈 색</span>
            <div class="cc-sw">{#each EYE_COLORS as c}<button class="s" class:on={eyeColor === c} style="background:{c}" on:click={() => (eyeColor = c)} aria-label="눈색"></button>{/each}</div>
            <span class="cc-l">눈 모양</span>
            <div class="cc-row wrap">{#each EYE_SHAPES as s}<button class="cc-pick sm" class:on={eyeShape === s.id} on:click={() => (eyeShape = s.id)}>{s.label}</button>{/each}</div>
            <div class="cc-srow"><span class="cc-l">눈 크기</span><span class="cc-poles">작게 ↔ 크게</span></div>
            <input type="range" min="1" max="8" step="1" bind:value={eyeSize} />
            <span class="cc-l">입 모양</span>
            <div class="cc-row wrap">{#each MOUTH_SHAPES as s}<button class="cc-pick sm" class:on={mouthShape === s.id} on:click={() => (mouthShape = s.id)}>{s.label}</button>{/each}</div>
            <div class="cc-srow"><span class="cc-l">입 크기</span><span class="cc-poles">작게 ↔ 크게</span></div>
            <input type="range" min="1" max="8" step="1" bind:value={mouthSize} />
          {/if}
        {:else if step === 2}
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
          <div class="cc-traits">
            {#each TRAITS as t}
              <div class="cc-trait">
                <div class="cc-srow"><span class="cc-l">{t.label}</span><span class="cc-poles">{t.low} ↔ {t.high}</span></div>
                <div class="cc-scale">
                  {#each SCALE as n}
                    <button
                      class="cc-num"
                      class:on={traits[t.axis] === n}
                      aria-label={`${t.label} ${n}단계`}
                      on:click={() => (traits = { ...traits, [t.axis]: n })}
                    ></button>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <ul class="cc-summary">
            <li><b>{name.trim() || "-"}</b> · {gender === "F" ? "여자" : "남자"}</li>
            {#if birthdayStr()}<li>생일 · {birthdayStr()}</li>{/if}
            {#if age}<li>나이 · {age}</li>{/if}
            <li>목소리 · {VOICE_PRESETS.find((v) => v.id === voicePreset)?.label}</li>
          </ul>
          {#if !nameOk}
            <button class="cc-namewarn" on:click={() => (step = 0)}>이름을 지어 주세요<span class="cc-ic">{@html ICON_RIGHT}</span></button>
          {/if}
        {/if}

        <div class="cc-nav">
          {#if step > 0}<button class="cc-ghost" on:click={() => (step -= 1)}><span class="cc-ic">{@html ICON_LEFT}</span>이전</button>{/if}
          <div class="cc-grow"></div>
          {#if step < STEPS.length - 1}
            <button class="cc-go" on:click={() => (step += 1)}>다음<span class="cc-ic">{@html ICON_RIGHT}</span></button>
          {:else}
            <button class="cc-go" disabled={busy || !nameOk} on:click={finish}>마을에 데려오기</button>
          {/if}
        </div>
        {/if}
        </div>
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
    height: 34px; padding: 0 14px 0 11px; border: 0; border-radius: 999px;
    background: rgba(255, 255, 255, 0.85); color: var(--pt-d);
    font-weight: 800; font-size: 13px; cursor: pointer;
    display: inline-flex; align-items: center; gap: 3px;
    box-shadow: 0 2px 8px rgba(40, 110, 85, 0.18);
  }
  .cc-preview {
    width: 46%; position: relative;
    background: radial-gradient(120% 100% at 50% 22%, #f0fbf5 0%, #c8f0dd 60%, #9fe3c4 100%);
    display: flex; align-items: flex-end; justify-content: center;
  }
  /* 무대 비네트 — 가장자리를 살짝 눌러 가운데 캐릭터가 도드라지게. */
  .cc-preview::after {
    content: ""; position: absolute; inset: 0; pointer-events: none;
    box-shadow: inset 0 0 140px rgba(47, 143, 110, 0.22);
  }
  .cc-preview canvas { position: absolute; inset: 0; width: 100%; height: 100%; outline: none; }
  .cc-namechip {
    position: relative; margin-bottom: 16px; z-index: 1;
    background: #fff; color: var(--pt-d); font-weight: 800;
    padding: 5px 16px; border-radius: 999px; box-shadow: 0 3px 10px rgba(40, 110, 85, 0.22);
  }
  .cc-form {
    flex: 1; display: flex; padding: 28px; overflow-y: auto; box-sizing: border-box;
  }
  /* 떠다니는 라벨 묶음이 아니라 "메뉴판" 한 장 — 카드로 담아 무대(미리보기)와 대칭. */
  .cc-card {
    margin: auto; width: 100%; max-width: 460px; box-sizing: border-box;
    background: #fff; border-radius: 26px; padding: 26px 28px 20px;
    display: flex; flex-direction: column;
    box-shadow: 0 18px 48px rgba(40, 110, 85, 0.16);
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
  /* 이름 — 입력칸이 아니라 네임플레이트(테두리 없는 큰 중앙 정렬). */
  .cc-name {
    width: 100%; box-sizing: border-box; margin: 2px 0 4px; padding: 12px 14px;
    border: 0; border-radius: 16px; background: var(--pt-bg); outline: none;
    font-family: inherit; font-size: 22px; font-weight: 800; text-align: center;
    color: var(--pt-d);
  }
  .cc-name::placeholder { color: #a9c4ba; font-weight: 700; font-size: 16px; }
  .cc-name:focus { background: #ddf6ea; }
  /* 생일/나이 ± 스테퍼 */
  .cc-step {
    flex: 1; display: flex; align-items: center; justify-content: space-between;
    background: var(--pt-bg); border-radius: 14px; padding: 5px 6px;
  }
  .cc-stepb {
    width: 32px; height: 32px; flex: 0 0 auto; border: 0; border-radius: 10px;
    background: #fff; color: var(--pt-d); cursor: pointer; font-size: 16px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 1px 3px rgba(40, 110, 85, 0.16);
  }
  .cc-stepv { font-weight: 800; color: var(--ink); font-size: 16px; }
  .cc-stepv i { font-style: normal; font-weight: 700; color: var(--muted); font-size: 12px; margin-left: 2px; }
  /* 버튼 안 아이콘 — 텍스트와 가운데 정렬. */
  .cc-ic { display: inline-flex; vertical-align: middle; font-size: 15px; }
  .cc-row { display: flex; gap: 8px; }
  .cc-row.wrap { flex-wrap: wrap; }
  .cc-pick {
    flex: 1; padding: 11px 0; border: 2px solid var(--pt-l); border-radius: 12px;
    background: #fff; color: #4f7d6c; font-weight: 700; cursor: pointer; font-size: 14px;
  }
  .cc-pick.sm { flex: 0 0 auto; padding: 9px 14px; font-size: 13px; }
  .cc-pick.on { border-color: var(--pt); background: var(--pt-bg); color: var(--pt-d); }
  .cc-hair {
    flex: 0 0 auto; width: 76px; padding: 6px 6px 8px; border: 2px solid var(--pt-l);
    border-radius: 12px; background: #fff; color: #4f7d6c; font-weight: 700;
    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 2px;
  }
  .cc-hair img { width: 60px; height: 60px; object-fit: contain; }
  .cc-hair span { font-size: 12px; }
  .cc-hair.on { border-color: var(--pt); background: var(--pt-bg); color: var(--pt-d); }
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
  .cc-ghost {
    border: 0; background: none; color: var(--muted); font-weight: 700; cursor: pointer;
    display: inline-flex; align-items: center; gap: 2px;
  }
  .cc-go {
    border: 0; padding: 11px 18px; border-radius: 999px; cursor: pointer;
    background: var(--pt); color: #fff; font-weight: 800; font-size: 14px;
    display: inline-flex; align-items: center; gap: 4px;
    box-shadow: 0 4px 12px rgba(94, 200, 160, 0.45);
  }
  .cc-go:disabled { opacity: 0.6; cursor: not-allowed; }
  .cc-namewarn {
    width: 100%; margin-top: 10px; padding: 9px; border: 0; border-radius: 10px;
    background: #fff0f3; color: #d6607f; font-weight: 700; font-size: 13px; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  }
</style>
