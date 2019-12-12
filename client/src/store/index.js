import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    entities: {},
    maps: {},
    selectedEntity: null,
    selectedMap: null,
  },
  mutations: {
    setEntities (state, entities) { state.entities = entities },
    setMaps (state, maps) { state.maps = maps },
    setSelectedEntity (state, selected) { state.selectedEntity = selected },
    setSelectedMap (state, selected) { state.selectedMap = selected }
  },
  actions: {
    setEntities: ({ commit }, entities) => commit('setEntities', entities),
    setMaps: ({ commit }, maps) => commit('setMaps', maps),
    setSelectedEntity: ({ commit }, selected) => commit('setSelectedEntity', selected),
    setSelectedMap: ({ commit }, selected) => commit('setSelectedMap', selected)
  },
  getters: {
    entities: state => state.entities,
    maps: state => state.maps,
    selectedEntity: state => state.selectedEntity,
    selectedMap: state => state.selectedMap
  },
  modules: {
  }
})
