<template>
  <v-app>
    <!-- <lmap/> -->
    <entity-infobox/>
  </v-app>
</template>

<script>
import Vue from 'vue'
import entityInfobox from './components/EntityInfobox'
// import entityInfobox from './components/EntityPopover'
import Map from './components/Map'

// Initialize with default components
const components = {
  // entityInfobox: entityPopover,
  entityInfobox: entityInfobox,
  lmap: Map
}

// Override defaults with custom components
if (window.data && window.data.customComponents) {
  for (let componentId in window.data.customComponents) {
    if (components[componentId]) {
      components[componentId] = `url:${window.data.customComponents[componentId]}`
    }
  }
}

export default {
  name: 'app',
  components,
  mounted() {
    this.$nextTick(() =>  this.init())
  },
  methods: {
    init() {
      // attach click listeners to entities
      document.body.querySelectorAll('.entity').forEach((entity) => {
        entity.addEventListener('click', this.onEntityClick)
      })
      // create maps for figure.map elements
      document.body.querySelectorAll('figure').forEach((figure) => {
        if (figure.classList.contains('map')) {
          const propsData = {
            zoom: figure.attributes['data-zoom'] ? parseInt(figure.attributes['data-zoom'].value) : 10,
            center: figure.attributes['data-center'].value.split(',').map(val => parseFloat(val)),
            mapid: figure.attributes.id ? figure.attributes.id.value : 'map-1',
            width: figure.attributes.width ? figure.attributes.width.value : '400px',
            height: figure.attributes.height ? figure.attributes.height.value : '400px'
          }
          const MapCtor = Vue.extend(Map)
          new MapCtor({ propsData, store: this.$store }).$mount(figure)
        }
      })
    },
    onEntityClick(e) {
      this.$store.dispatch('setSelectedEntity', e.target.attributes['data-qid'].value)
    }
  }}
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
