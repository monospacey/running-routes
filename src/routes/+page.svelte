<script>
  import RadiusMap from "../lib/RadiusMap.svelte";
  import RunningMap from "../lib/RunningMap.svelte";

  let radiusMapCheck = false;
</script>

<h1>Running Routes</h1>
<div>
  <input type="checkbox" bind:checked={radiusMapCheck} />
  Tick for the two maps
</div>

{#if radiusMapCheck}
  <RunningMap />
{:else}
  <RadiusMap />
{/if}
