<script lang="ts">
  import { toastMsg } from "../lib/store";
</script>

<div id="toast" class:show={$toastMsg}>{$toastMsg}</div>
