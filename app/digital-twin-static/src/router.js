import Vue from 'vue'
import Router from 'vue-router'
import Projects from './views/Projects.vue'
import Wizard from './views/Wizard.vue'
import Equipment from './views/Equipment.vue'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'home',
      component: Wizard
    },
    {
      path: '/projects',
      name: 'Projects',
      component: Projects
    },
    {
      path: '/equipment',
      name: 'Equipment',
      component: Equipment
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (about.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import(/* webpackChunkName: "about" */ './views/About.vue')
    }
  ]
})
