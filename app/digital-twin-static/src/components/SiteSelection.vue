<template>
  <v-mapbox
    ref="mapbox"
    class="map"
    access-token="pk.eyJ1Ijoic2lnZ3lmIiwiYSI6Il8xOGdYdlEifQ.3-JZpqwUa3hydjAJFXIlMA"
    map-style="mapbox://styles/mapbox/satellite-streets-v10"
    :center="[5.2, 53]"
    :zoom="10">
  </v-mapbox>
</template>
<script>
import Vue2MapboxGl from 'vue2mapbox-gl'
import Vue from 'vue'

import MapboxDraw from '@mapbox/mapbox-gl-draw'

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
