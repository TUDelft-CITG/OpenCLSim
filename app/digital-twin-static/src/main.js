import 'material-design-icons-iconfont/dist/material-design-icons.css'
import 'mapbox-gl/dist/mapbox-gl.css'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'

import Vue from 'vue'
import './plugins/vuetify'
import App from './App.vue'
import router from './router'
import store from './store'

import Vuetify from 'vuetify'

Vue.config.productionTip = false

Vue.use(Vuetify)
new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
