<script>
  import downloader from "./osmg";

  import Graph from "graphology";
  import { cropToLargestConnectedComponent } from "graphology-components";
  import astar from "graphology-shortest-path/astar";
  import dijkstra from "graphology-shortest-path/dijkstra";
  import { kmeans } from "ml-kmeans";
  import L from "leaflet";
  import utmObj from "utm-latlng";

  var utm = new utmObj();

  let map;
  let coordinate;
  let innerCircle;
  let outerCircle;
  let distance = 1000;
  let radiusBuffer = 150;
  let coordinateMarker;
  let zoneNumber;
  let zoneLetter;
  let precision = 1;
  let graph = new Graph({
    allowSelfLoops: false,
    multi: false,
    type: "undirected",
  });

  async function foo() {
    // Find UTM information on the center coordinate
    let pointUtmOutput = utm.convertLatLngToUtm(
      -37.818078,
      144.96681,
      precision
    );
    console.log(pointUtmOutput);
    zoneLetter = pointUtmOutput.ZoneLetter;
    zoneNumber = pointUtmOutput.ZoneNumber;

    // Download and process the graph
    let temp_response = await downloader(distance / 2, -37.818078, 144.96681);
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
    cropToLargestConnectedComponent(graph);

    // Draw the edges on the graph
    // graph.forEachEdge(
    //   (
    //     edge,
    //     attributes,
    //     source,
    //     target,
    //     sourceAttributes,
    //     targetAttributes
    //   ) => {
    //     L.polyline(
    //       Array(
    //         Array(sourceAttributes.lat, sourceAttributes.lon),
    //         Array(targetAttributes.lat, targetAttributes.lon)
    //       )
    //     ).addTo(map);
    //   }
    // );

    // Run K Means over the X and Y coordinates
    let kMeansData = graph.mapNodes((node, attributes) => {
      return [attributes.x, attributes.y];
    });
    console.log(graph.order);
    let kMeansAns = kmeans(kMeansData, 50);
    const centroidArray = kMeansAns.centroids.map((e) => {
      return utm.convertUtmToLatLng(e[0], e[1], zoneNumber, zoneLetter);
    });
    centroidArray.map((e) => {
      L.marker([e.lat, e.lng]).addTo(map);
    });

    let medoids = kMeansAns.centroids.map((e) => {
      let nodeDistances = graph.mapNodes((node, attributes) => {
        return {
          node: node,
          distance: Math.hypot(attributes.x - e[0], attributes.y - e[1]),
        };
      });
      return nodeDistances.reduce((prev, curr) => {
        return prev.distance < curr.distance ? prev : curr;
      }).node;
    });
    console.log(medoids);

    // Run A* to find shortest distances
    console.log("Finding shortest path");
    let path = dijkstra.bidirectional(
      graph,
      medoids[0],
      medoids[1],
      "distance"
    );
    L.polyline(
      path.map((node) => {
        return [
          graph.getNodeAttribute(node, "lat"),
          graph.getNodeAttribute(node, "lon"),
        ];
      })
    ).addTo(map);
    let total = 0
    for (let i = 0; i < path.length - 1; i ++) {
      total += graph.getEdgeAttribute(path[i], path[i + 1], "distance")
    }
    console.log(total)
  }
  function initMap() {
    coordinate = [-37.818078, 144.96681];
    map = L.map("map", { zoomSnap: 0 }).setView(coordinate, 13);
    L.tileLayer(
      "https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }
    ).addTo(map);

    innerCircle = L.circle(coordinate, { radius: distance / 2 }).addTo(map);
    outerCircle = L.circle(coordinate, {
      radius: distance / 2 + radiusBuffer,
      fillOpacity: 0,
      opacity: 0,
    }).addTo(map);
    coordinateMarker = L.marker(coordinate).addTo(map);

    updateShapes();
    flyToBounds();
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
<button on:click={foo}>Hello</button>

<style>
  #map {
    width: 90%;
    margin-left: auto;
    margin-right: auto;
    height: 80%;
    border-radius: 3%;
  }
</style>
