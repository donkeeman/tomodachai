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
  import { logOpen } from "./lib/store";

  let canvas: HTMLCanvasElement;
  onMount(() => { startSim(canvas); });
</script>

<canvas id="renderCanvas" bind:this={canvas}></canvas>
<Hud />
<Toast />
{#if $logOpen}<EventLog />{/if}
<Toolbar />
<Album />
<RankBoard />
<Card />
<BubbleBox />
<ExitButton />
<CharacterCreate />
<Fade />
<ErrBanner />
