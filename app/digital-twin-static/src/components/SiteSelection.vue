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
import _ from 'lodash'

import MapboxDraw from '@mapbox/mapbox-gl-draw'

import 'mapbox-gl/dist/mapbox-gl.css'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'

Vue.use(Vue2MapboxGl)

export default {
  name: 'site-selection',
  props: {
    'site': Object
  },
  data () {
    return {
      draw: null
    }
  },
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
    this.draw = new MapboxDraw(options)
    map.addControl(this.draw, 'top-left')
    map.on('draw.create', this.updateFeatures)
    map.on('draw.delete', this.updateFeatures)
    map.on('draw.update', this.updateFeatures)
    this.$nextTick(() => {
      // not sure why this is needed
      map.resize()
    })
  },
  methods: {
    updateFeatures () {
      let features = this.draw.getAll()
      // perhaps use vuex or features
      _.each(features.features, (feature, index) => {
        feature.properties.capacity = 1000
        feature.properties.name = 'Site' + index
      })

      Vue.set(this.site, 'features', features)
    }
  }

}

</script>
