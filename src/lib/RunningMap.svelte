<script>
  import downloader from "./osmg";
  import genetic from "./genetic";

  import Graph from "graphology";
  import { cropToLargestConnectedComponent } from "graphology-components";
  import dijkstra from "graphology-shortest-path/dijkstra";
  import { edgePathFromNodePath } from "graphology-shortest-path";
  import { kmeans } from "ml-kmeans";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import utmObj from "utm-latlng";

  var utm = new utmObj();

  let map;
  let coordinate;
  let innerCircle;
  let outerCircle;
  let distance = 1500;
  let radiusBuffer = 100;
  let coordinateMarker;
  let zoneNumber;
  let zoneLetter;
  let precision = 1;
  let graph = new Graph({
    allowSelfLoops: false,
    multi: false,
    type: "undirected",
  });
  let medoidGraph = new Graph({
    allowSelfLoops: false,
    multi: false,
    type: "undirected",
  });
  let resultFlag = false;
  let total;
  function onLocationFound(e) {
    coordinate = { lat: e.latitude, lon: e.longitude };
    coordinateMarker.setLatLng([coordinate.lat, coordinate.lon]);
    updateShapes();
    flyToBounds();
  }
  function onLocationError(e) {
    alert(e.message);
  }
  function updateShapes() {
    if (map) {
      const coordinateArray = [coordinate.lat, coordinate.lon];
      console.log(coordinateArray);
      innerCircle.setLatLng(coordinateArray);
      outerCircle.setLatLng(coordinateArray);
      coordinateMarker.setLatLng(coordinateArray);

      innerCircle.setRadius(distance / 2);
      outerCircle.setRadius(distance / 2 + radiusBuffer);
    }
  }

  function flyToBounds() {
    if (map) {
      map.flyToBounds(outerCircle.getBounds());
    }
  }
  async function foo() {
    // Find UTM information on the center coordinate
    console.log(coordinate);
    let pointUtmOutput = utm.convertLatLngToUtm(
      coordinate.lat,
      coordinate.lon,
      precision
    );
    zoneLetter = pointUtmOutput.ZoneLetter;
    zoneNumber = pointUtmOutput.ZoneNumber;

    // Download and process the graph
    let temp_response = await downloader(
      distance / 2 + radiusBuffer,
      coordinate.lat,
      coordinate.lon
    );
    console.log(temp_response);

    temp_response.elements.map((element) => {
      for (let i = 0; i < element.nodes.length - 1; i++) {
        let oldNode = element.nodes[i];
        let oldLatitude = element.geometry[i].lat;
        let oldLongitude = element.geometry[i].lon;
        let oldUtmOutput = utm.convertLatLngToUtm(oldLatitude, oldLongitude, 1);
        let oldX = oldUtmOutput.Easting;
        let oldY = oldUtmOutput.Northing;
        graph.mergeNode(oldNode, {
          lat: oldLatitude,
          lon: oldLongitude,
          x: oldX,
          y: oldY,
        });

        let newNode = element.nodes[i + 1];
        let newLatitude = element.geometry[i + 1].lat;
        let newLongitude = element.geometry[i + 1].lon;
        let newUtmOutput = utm.convertLatLngToUtm(newLatitude, newLongitude, 1);
        let newX = newUtmOutput.Easting;
        let newY = newUtmOutput.Northing;
        graph.mergeNode(newNode, {
          lat: newLatitude,
          lon: newLongitude,
          x: newX,
          y: newY,
        });

        graph.mergeEdge(oldNode, newNode, {
          distance: Math.hypot(newX - oldX, newY - oldY),
        });
      }
    });
    // Drop any nodes outside the radius
    graph.mapNodes((node, attributes) => {
      if (
        Math.hypot(
          attributes.x - pointUtmOutput.Easting,
          attributes.y - pointUtmOutput.Northing
        ) >
        distance / 2
      ) {
        graph.dropNode(node);
      }
    });

    // Only look at largest connected component
    cropToLargestConnectedComponent(graph);

    // Run K-Means over the X and Y coordinates
    let kMeansData = graph.mapNodes((node, attributes) => [
      attributes.x,
      attributes.y,
    ]);
    console.log(kMeansData.length);

    let kMeansAns = kmeans(
      kMeansData,
      Math.max(50, Math.floor(0.01*kMeansData.length))
    );

    // Find the medoids from K-Means
    console.log(typeof kMeansAns.centroids);
    console.log([pointUtmOutput.Easting, pointUtmOutput.Northing]);
    console.log(kMeansAns.centroids);
    let centerAndCentroids = [
      [pointUtmOutput.Easting, pointUtmOutput.Northing],
    ].concat(kMeansAns.centroids);
    let rawMedoids = [];
    centerAndCentroids.forEach((e) => {
      var nodeDistances = graph.mapNodes((node, attributes) => {
        return {
          node: node,
          distance: Math.hypot(attributes.x - e[0], attributes.y - e[1]),
        };
      });
      let closestNode = nodeDistances.reduce((prev, curr) =>
        prev.distance < curr.distance ? prev : curr
      );
      rawMedoids.push(closestNode.node);
    });

    // Deduplicate using set
    // Set keeps the first instance of the array
    let medoids = [...new Set(rawMedoids)];
    let medoidData = {};
    console.log("Calculating single source");
    medoids.map((u) => {
      const paths = dijkstra.singleSource(graph, u);
      for (const v in paths) {
        let distance = edgePathFromNodePath(graph, paths[v]).reduce(
          (accumulator, currentValue) =>
            accumulator + graph.getEdgeAttribute(currentValue, "distance"),
          0
        );

        medoidData[`${u}}-${v}`] = { path: paths[v], distance: distance };
        medoidData[`${v}}-${u}`] = { path: paths[v].reverse(), distance: distance };
      }
    });
    var medoidCombinations = medoids.flatMap((v, i) =>
      medoids.slice(i + 1).map((w) => [v, w])
    );
    medoidCombinations.map((v) => {
      let nodePath = dijkstra.bidirectional(graph, v[0], v[1], "distance");
      let distance = edgePathFromNodePath(graph, nodePath).reduce(
        (accumulator, currentValue) =>
          accumulator + graph.getEdgeAttribute(currentValue, "distance"),
        0
      );
      medoidGraph.mergeNode(v[0], graph.getNodeAttributes(v[0]));
      medoidGraph.mergeNode(v[1], graph.getNodeAttributes(v[1]));
      medoidGraph.mergeEdge(v[0], v[1], {
        nodePath: nodePath,
        distance: distance,
      });
    });
    let medoidNodes = {};
    medoidGraph.forEachNode((node, attr) => (medoidNodes[node] = attr));
    let medoidEdges = {};
    medoidGraph.forEachEdge((edge, attr, source, target) => {
      medoidEdges[`${source}-${target}`] = attr.distance;
      medoidEdges[`${target}-${source}`] = attr.distance;
    });
    console.log("Attributes of rootMedoid");
    console.log(medoidGraph.getNodeAttributes(medoids[0]));
    // genetic algorithm!
    var config = {
      iterations: 500,
      size: 250,
      crossover: 0.7,
      mutation: 0.3,
      skip: 50,
      webWorkers: false,
    };
    let userData = {
      medoidNodes: medoidNodes,
      medoidEdges: medoidEdges,
      distance: distance,
      rootMedoid: medoids[0],
      solution: [],
    };

    genetic.evolve(config, userData);
    console.log(genetic.lastSolution);
    let nodePath = genetic.lastSolution.niceRoute;

    // Find node path
    // let nodePath = medoids.slice(0, 8).concat([medoids[0]]);
    console.log("NodePath");
    console.log(nodePath);
    // nodePath.map((value, index) => {
    //   L.marker(
    //     [
    //       graph.getNodeAttribute(value, "lat"),
    //       graph.getNodeAttribute(value, "lon"),
    //     ],
    //   ).addTo(map);
    // });
    L.marker(
      [
        graph.getNodeAttribute(nodePath[0], "lat"),
        graph.getNodeAttribute(nodePath[0], "lon"),
      ],
      { title: "ROot" }
    ).addTo(map);
    total = edgePathFromNodePath(medoidGraph, nodePath).reduce(
      (accumulator, currentValue) =>
        accumulator + medoidGraph.getEdgeAttribute(currentValue, "distance"),
      0
    );
    for (let n = 0; n < nodePath.length - 1; n++) {
      let path = medoidGraph.getEdgeAttribute(
        nodePath[n],
        nodePath[n + 1],
        "nodePath"
      );
      L.polyline(
        path.map((node) => {
          return [
            graph.getNodeAttribute(node, "lat"),
            graph.getNodeAttribute(node, "lon"),
          ];
        }),
        { weight: 5 }
      ).addTo(map);
    }
    console.log(total.toLocaleString(undefined, { maximumFractionDigits: 0 }));
    let mapsUrl = "https://www.google.com/maps/dir/";
    let fullMapsUrl = nodePath.reduce(
      (accumulator, currentValue) =>
        accumulator.concat(
          `${graph.getNodeAttribute(currentValue, "lat")},${graph.getNodeAttribute(currentValue, "lon")}/`
        ),
      mapsUrl
    );
    console.log(fullMapsUrl.concat("data=!4m2!4m1!3e2"));

    const smallestX = nodePath.reduce((prev, curr) =>
      graph.getNodeAttribute(prev, "x") < graph.getNodeAttribute(curr, "x")
        ? prev
        : curr
    );
    const largestX = nodePath.reduce((prev, curr) =>
      graph.getNodeAttribute(prev, "x") > graph.getNodeAttribute(curr, "x")
        ? prev
        : curr
    );
    const smallestY = nodePath.reduce((prev, curr) =>
      graph.getNodeAttribute(prev, "y") < graph.getNodeAttribute(curr, "y")
        ? prev
        : curr
    );
    const largestY = nodePath.reduce((prev, curr) =>
      graph.getNodeAttribute(prev, "y") > graph.getNodeAttribute(curr, "y")
        ? prev
        : curr
    );
    console.log(smallestX, smallestY, largestX, largestY);
    console.log(pointUtmOutput);
    utm.convertUtmToLatLng();
    const boundOne = utm.convertUtmToLatLng(
      graph.getNodeAttribute(smallestX, "x") - radiusBuffer,
      graph.getNodeAttribute(smallestY, "y") - radiusBuffer,
      zoneNumber,
      zoneLetter
    );
    const boundTwo = utm.convertUtmToLatLng(
      graph.getNodeAttribute(largestX, "x") + radiusBuffer,
      graph.getNodeAttribute(largestY, "y") + radiusBuffer,
      zoneNumber,
      zoneLetter
    );
    console.log([
      [boundOne.lat, boundOne.lng],
      [boundTwo.lat, boundTwo.lng],
    ]);
    innerCircle.setStyle({ fillOpacity: 0, opacity: 0 });
    outerCircle = L.rectangle(
      [
        [boundOne.lat, boundOne.lng],
        [boundTwo.lat, boundTwo.lng],
      ],
      { fillOpacity: 0, opacity: 0 }
    );

    flyToBounds();
    resultFlag = true;
  }
  function initMap() {
    coordinate = { lat: -37.818078, lon: 144.96681 };
    map = L.map("map", { zoomSnap: 0 }).setView(coordinate, 13);
    // L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    //   attribution:
    //     '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    // }).addTo(map);
    L.tileLayer(
      "https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        updateWhenZooming: false,
      }
    ).addTo(map);
    innerCircle = L.circle([coordinate.lat, coordinate.lon], {
      radius: distance / 2,
    }).addTo(map);
    outerCircle = L.circle([coordinate.lat, coordinate.lon], {
      radius: distance / 2 + radiusBuffer,
      fillOpacity: 0,
      opacity: 0,
    }).addTo(map);
    coordinateMarker = L.marker([coordinate.lat, coordinate.lon]).addTo(map);
    flyToBounds()
    map.locate();
    map.on("locationfound", onLocationFound);
    map.on("locationerror", onLocationError);
  }
</script>

<!-- <svelte:head>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
</svelte:head> -->

<div id="map" use:initMap></div>

{#if !resultFlag}
  <h3>
    I want to run {distance.toLocaleString(undefined, {
      maximumFractionDigits: 0,
    })} meters.
  </h3>
  <input
    type="range"
    min="1500"
    max="10000"
    bind:value={distance}
    on:input={updateShapes}
    on:input={flyToBounds}
    class="slider"
    id="myRange"
  />
  <button on:click={foo}>Search</button>
{:else}
  <h3>
    Estimated distance: {total.toLocaleString(undefined, {
      maximumFractionDigits: 0,
    })} meters
  </h3>
{/if}

<style>
  #map {
    width: 80%;
    margin-left: auto;
    margin-right: auto;
    height: 70%;
    border-radius: 3%;
  }
</style>
