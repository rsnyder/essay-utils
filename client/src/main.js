import Vue from 'vue'
import Vuetify from 'vuetify'
import VTooltip from 'v-tooltip'
import httpVueLoader from 'http-vue-loader'
import App from './App.vue'
import store from './store'
import '../assets/styles/main.css'

function initApp() {
  console.log('essay-utils')

  const vueAppElem = document.createElement('div')
  vueAppElem.id = 'app1'
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
  })
  vm.$mount('#app1')

  document.querySelectorAll('script[type="application/ld+json"]').forEach((scr) => {
    console.log(scr)
    eval(scr.text)
  })

  if (window.data) {
    vm.$store.dispatch('setEntities', window.data.entities)
    vm.$store.dispatch('setMaps', window.data.maps)
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const waitForContent = setInterval(() => {
    const esssayElem = document.getElementById('essay')
    if (esssayElem && esssayElem.innerText.length > 0) {
      console.log('essay found', esssayElem.innerText.length)
      console.log(esssayElem)
      clearInterval(waitForContent)
      initApp()
    }
  }, 1000)
}, false)
