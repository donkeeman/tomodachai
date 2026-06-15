<script lang="ts">
  import { errorMsg } from "../lib/store";
</script>

{#if $errorMsg}
  <div id="err">{$errorMsg}</div>
{/if}
