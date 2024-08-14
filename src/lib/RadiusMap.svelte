<script>
  import L from "leaflet";

  let map;
  let coordinate;
  let innerCircle;
  let outerCircle;
  let distance = 1000;
  let radiusBuffer = 150;
  let coordinateMarker;

  function onLocationFound(e) {
    coordinate = e.latlng
    updateShapes()
    flyToBounds()
  }
  function onLocationError(e) {
    alert(e.message)
  }
  function initMap() {
    coordinate = [-37.818078, 144.96681];
    map = L.map("map", { zoomSnap: 0 }).setView(coordinate, 13);
    // L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    L.tileLayer("https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    innerCircle = L.circle(coordinate, { radius: distance / 2 }).addTo(map);
    outerCircle = L.circle(coordinate, {
      radius: distance / 2 + radiusBuffer,
      fillOpacity: 0,
      opacity: 0,
    }).addTo(map);
    coordinateMarker = L.marker(coordinate).addTo(map);

    updateShapes();
    flyToBounds();
    map.locate();
    map.on("locationfound", onLocationFound)
    map.on("locationerror", onLocationError)
  }

  function updateShapes() {
    if (map) {
      innerCircle.setLatLng(coordinate);
      outerCircle.setLatLng(coordinate);
      coordinateMarker.setLatLng(coordinate);

      innerCircle.setRadius(distance / 2);
      outerCircle.setRadius(distance / 2 + radiusBuffer);
    }
  }

  function flyToBounds() {
    if (map) {
      map.flyToBounds(outerCircle.getBounds());
    }
  }
</script>

<svelte:head>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
</svelte:head>

<div id="map" use:initMap></div>

<h3>I want to run {distance} meters.</h3>
<input
  type="range"
  min="1000"
  max="10000"
  bind:value={distance}
  on:input={updateShapes}
  on:input={flyToBounds}
  class="slider"
  id="myRange"
/>

<style>
  #map {
    width: 90%;
    margin-left: auto;
    margin-right: auto;
    height: 80%;
    border-radius: 3%;
  }
</style>
