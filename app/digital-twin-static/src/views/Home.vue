<template>
  <v-flex fill-height fluid>
    <v-mapbox
      ref="mapbox"
      access-token="pk.eyJ1Ijoic2lnZ3lmIiwiYSI6Il8xOGdYdlEifQ.3-JZpqwUa3hydjAJFXIlMA"
      map-style="mapbox://styles/mapbox/satellite-streets-v10"
      :center="[5.2, 53]"
      :zoom="10">
    </v-mapbox>
  </v-flex>
</template>

<script>
// @ is an alias to /src
import Vue2MapboxGl from 'vue2mapbox-gl'
import Vue from 'vue'

import 'mapbox-gl/dist/mapbox-gl.css'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'

Vue.use(Vue2MapboxGl)
export default {
  name: 'home',
  components: {
  },
  mounted () {
    let map = this.$refs.mapbox.map
    let options = {
      controls: {
        point: true,
        line_string: true,
        polygon: true,
        trash: true
      },
      displayControlsDefault: false
    }
    let draw = new MapboxDraw(options)
    map.addControl(draw, 'top-left')
  }
}
</script>
<style>
  .mapboxgl-map {
  width: 100%;
  height: 100%;
  }
</style>
