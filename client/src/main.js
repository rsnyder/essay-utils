import Vue from 'vue'
import Vuetify from 'vuetify'
import VTooltip from 'v-tooltip'
import httpVueLoader from 'http-vue-loader'
import App from './App.vue'
import store from './store'

const vueAppElem = document.createElement('div')
vueAppElem.id = 'app'
document.body.appendChild(vueAppElem)

Vue.config.productionTip = false
Vue.config.devtools = true

Vue.use(Vuetify)
Vue.use(VTooltip)
Vue.use(httpVueLoader)
Vue.prototype.$L = L

const vm = new Vue({
  template: '<App/>',
  store,
  render: h => h(App),
  vuetify: new Vuetify()
}).$mount('#app')

if (window.data) {
  vm.$store.dispatch('setEntities', window.data.entities)
  vm.$store.dispatch('setMaps', window.data.maps)
}
