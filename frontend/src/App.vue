<script>
import "leaflet/dist/leaflet.css"
import { LMap, LCircle, LMarker, LTileLayer, LPolyline } from '@vue-leaflet/vue-leaflet';
import axios from 'axios';

export default {
  components: {
    LMap,
    LCircle,
    LMarker,
    LTileLayer,
    LPolyline,
    axios,
  },
  data() {
    return {
      colours: {
        "circle": "#b2182b"
      },
      circle: {
        radius: 2500
      },
      map: {
        zoom: 8,
        bounds: null,
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors'
      },
      user_inputs: {
        n: 5,
        distance: 3000,
        lat: -37.8102361,
        lng: 144.9627652,
      },
      api_output: [
        {"coordinates": [], "distance": 0},
        {"coordinates": [], "distance": 0},
        {"coordinates": [], "distance": 0},
        {"coordinates": [], "distance": 0},
        {"coordinates": [], "distance": 0}
      ]
    }
  },
  async created() {
    // get user's coordinates from browser request
    // this.$getLocation({})
    //   .then(coordinates => {
    //     this.myCoordinates = coordinates;
    //   })
    //   .catch(error => alert(error));
    //   navigator.geolocation.getCurrentPosition({})
    //     .then(coords => {
    //       this.coords = coords;
    //     })
    //     .catch(error => alert(error))
    // 
    navigator.geolocation.getCurrentPosition(
      position => {
        console.log("Read location from HTML5's gelocation")
        console.log([position.coords.latitude, position.coords.latitude])
        this.user_inputs.lat = position.coords.latitude;
        this.user_inputs.lng= position.coords.longitude;
      },
      error => {
        console.log(error.message);
        alert("Please refresh running-routes and share your location")
      }
    )
  },
  methods: {
    updateBounds(value) {
      this.$nextTick(() => {
        this.$refs.myMap.leafletObject.flyToBounds(
          this.$refs.outsideCircle.leafletObject.getBounds()
        )
      })
    },
    clickButton(value) {
      console.log("starting ")
      axios
        .get("https://running-routes-quubcdiruq-km.a.run.app/about")
        .then(res => {
          console.log("about success")
          console.log(res)
          })
        .catch(function(error) {
          console.log("about failure")
          console.log(error)
        })
      console.log(this.user_inputs.n) 
      console.log(this.user_inputs.distance) 
      console.log(this.user_inputs.lat) 
      console.log(this.user_inputs.lng) 
      axios
        .get(
          "https://running-routes-quubcdiruq-km.a.run.app/pipeline",
          {
            params:{
              n: this.user_inputs.n,
              distance: this.user_inputs.distance,
              lat: this.user_inputs.lat,
              lng: this.user_inputs.lng,
            }
          }
        )
        .then(res => {
          console.log(res)
          this.api_output[0].coordinates = res.data.routes[0].coordinates
          this.api_output[1].coordinates = res.data.routes[1].coordinates
          this.api_output[2].coordinates = res.data.routes[2].coordinates
          this.api_output[3].coordinates = res.data.routes[3].coordinates
          this.api_output[4].coordinates = res.data.routes[4].coordinates
        })
        .catch(function (error){
          console.log(error)
          console.log(error.data)
          console.log(error.status)
          console.log(error.headers)
        })
      }
    }
  }
</script>

<template>
  <header>
    <div>
      <h1>Running routes</h1>
      <h1>Hello Insights centre!</h1>
      <hr />
      <h2>I want to run</h2>
      <select v-model="user_inputs.distance" @change="updateBounds">
        <option>3000</option>
        <option>4000</option>
        <option>5000</option>
        <option>6000</option>
        <option>7000</option>
      </select>
      <h2>meters.</h2>
      <br />
      <span>inputs: {{ user_inputs.distance }}, {{ user_inputs.distance / 2 }}</span>
      <br />
      <button @click="clickButton">Generate</button>
      <br />
      <p>{{ user_inputs.lat }}</p>
      <p>{{ user_inputs.lng}}</p>
      <p>{{ map.bounds }}</p>
    </div>
  </header>

  <main>
    <div id="map"></div>
    <l-map
      ref="myMap"
      :bounds="this.map.bounds"
      :center="[this.user_inputs.lat, this.user_inputs.lng]"
      style="height:100%; width:100%"
    >
      <l-tile-layer :url="this.map.url" :attribution="this.map.attribution"></l-tile-layer>
      <l-marker :lat-lng="[user_inputs.lat, user_inputs.lng]" @move="updateBounds"></l-marker>
      <l-circle
        :lat-lng="[user_inputs.lat, user_inputs.lng]"
        :radius="(user_inputs.distance / 2)"
        :color="colours.circle"
      ></l-circle>
      <l-circle
        ref="outsideCircle"
        :lat-lng="[user_inputs.lat, user_inputs.lng]"
        :radius="(50 + (user_inputs.distance / 2))"
        :color="colours.circle"
        :opacity="0"
      ></l-circle>
      <l-polyline :lat-lngs="api_output[0].coordinates"></l-polyline>
      <l-polyline :lat-lngs="api_output[1].coordinates"></l-polyline>
      <l-polyline :lat-lngs="api_output[2].coordinates"></l-polyline>
      <l-polyline :lat-lngs="api_output[3].coordinates"></l-polyline>
      <l-polyline :lat-lngs="api_output[4].coordinates"></l-polyline>
    </l-map>
  </main>
</template>

<style>
@import "./assets/base.css";
body {
  padding: 0;
  margin: 0;
}
html,
body,
#myMap {
  height: 100%;
  width: 100vw;
}
#app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  font-weight: normal;
}
header {
  line-height: 1.5;
}
.logo {
  display: block;
  margin: 0 auto 2rem;
}
a,
.green {
  text-decoration: none;
  color: hsla(160, 100%, 37%, 1);
  transition: 0.4s;
}
@media (hover: hover) {
  a:hover {
    background-color: hsla(160, 100%, 37%, 0.2);
  }
}
@media (min-width: 1024px) {
  body {
    display: flex;
    place-items: center;
  }
  #app {
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 0 2rem;
  }
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }
  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }
  .logo {
    margin: 0 2rem 0 0;
  }
}
</style>