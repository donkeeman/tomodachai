<script lang="ts">
  import { onMount } from "svelte";
  import { startSim } from "./lib/sim";
  import Hud from "./components/Hud.svelte";
  import Toast from "./components/Toast.svelte";
  import EventLog from "./components/EventLog.svelte";
  import Card from "./components/Card.svelte";
  import BubbleBox from "./components/BubbleBox.svelte";
  import RankBoard from "./components/RankBoard.svelte";
  import Album from "./components/Album.svelte";
  import Toolbar from "./components/Toolbar.svelte";
  import ExitButton from "./components/ExitButton.svelte";
  import Fade from "./components/Fade.svelte";
  import ErrBanner from "./components/ErrBanner.svelte";
  import CharacterCreate from "./components/CharacterCreate.svelte";

  let canvas: HTMLCanvasElement;
  onMount(() => { startSim(canvas); });
</script>

<canvas id="renderCanvas" bind:this={canvas}></canvas>
<Hud />
<Toast />
<EventLog />
<Toolbar />
<Album />
<RankBoard />
<Card />
<BubbleBox />
<ExitButton />
<CharacterCreate />
<Fade />
<ErrBanner />
<div id="hint">드래그 회전 · 우클릭/Shift·방향키 이동 · 휠/핀치 줌 · 주민 클릭=정보 · 주민 근처로 가면 자동 따라가기 · 더블클릭 전체보기</div>
