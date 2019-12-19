<template>
  <v-app>
    <entity-infobox/>
    <bottom-sheet/>
  </v-app>
</template>

<script>
import Vue from 'vue'
import { throttle } from 'lodash'
import entityInfobox from './components/EntityInfobox'
import bottomSheet from './components/BottomSheet'
import { get_entity } from './api'

// Initialize with default components
const components = {
  entityInfobox,
  bottomSheet
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
  data: () => ({
    // activeSection: null
  }),
  computed: {
    activeSections() { return this.$store.getters.activeSections },
    activeSection() { return this.activeSections.length > 0 ? this.activeSections[0] : null }
  },
  mounted() {
    this.$nextTick(() => this.init())
  },
  methods: {
    init() {
      this.findSections()
      // add scroll listener to update visible sections list in store
      window.addEventListener('scroll', this.handleScroll)

      // attach click listeners to entities
      document.body.querySelectorAll('.entity').forEach((entity) => {
        entity.addEventListener('click', this.onEntityClick)
      })
      // this.addMaps()
    },
    addMaps() {
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
          const MapConstructor = Vue.extend(Map)
          const mnt = new MapConstructor({ propsData, store: this.$store }).$mount(figure)
        }
      })
    },
    onEntityClick(e) {
      const qid = e.target.attributes['data-qid'].value
      this.$store.dispatch('setSelectedEntityQID', qid)
      if (!this.$store.state.entities[qid]['wikipedia summary']) {
        get_entity(`wd:${qid}`)
        .then((entity) => {
          entity.qid = qid
          this.$store.dispatch('setEntity', entity)
        })
      }
    },
    findSections() {
      const sections = []
      for (let i = 1; i < 9; i++) {
        document.body.querySelectorAll(`h${i}`).forEach((heading) => {
          const section = heading.parentElement
          sections.push(
            {
              id: section.attributes.id.value,
              level: i,
              top: section.offsetTop,
              bottom: section.offsetTop + section.offsetHeight
            }
          )
        })
      }
      this.$store.dispatch('setDocumentSections', sections)
    },
    handleScroll: throttle(function (event) {
      const elem = event.target.scrollingElement
      const activeSections = []
      this.$store.getters.documentSections.forEach((section) => {
        if (elem.scrollTop >= section.top && elem.scrollTop <= section.bottom) {
          activeSections.push(`${section.level}: ${section.id}`)
        }
      })
      activeSections.sort().reverse()
      if (activeSections.length > 0 && activeSections[0] !== this.activeSection) {
        this.$store.dispatch('setActiveSections', activeSections)        
      }
    }, 200)
  }
}
</script>

<style>
  #app {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    color: #2c3e50;
  }
  .v-application--wrap {
    min-height: 0 !important;
  }
</style>
