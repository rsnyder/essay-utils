import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    entities: {},
    maps: {},
    selectedEntityQID: null,
    selectedMapID: null,
    documentSections: [],
    activeSections: [],
    selectedSection: null
  },
  mutations: {
    setEntities (state, entities) { state.entities = entities },
    setEntity (state, entity) {
      const entities = { ...state.entities }
      entities[entity.qid] = entity
      state.entities = entities
    },
    setMaps (state, maps) { state.maps = maps },
    setSelectedEntityQID (state, qid) { state.selectedEntityQID = qid },
    setSelectedMapID (state, mapid) { state.setSelectedMapID = mapid },
    setDocumentSections (state, sections) { state.documentSections = sections },
    setActiveSections (state, sections) { state.activeSections = sections },
    setSelectedSection (state, sectionId) { state.selectedEntityQID = sectionId },
  },
  actions: {
    setEntities: ({ commit }, entities) => commit('setEntities', entities),
    setEntity: ({ commit }, entity) => commit('setEntity', entity),
    setMaps: ({ commit }, maps) => commit('setMaps', maps),
    setSelectedEntityQID: ({ commit }, qid) => commit('setSelectedEntityQID', qid),
    setSelectedMapID: ({ commit }, mapid) => commit('setSelectedMapID', mapid),
    setDocumentSections: ({ commit }, sections) => commit('setDocumentSections', sections),
    setActiveSections: ({ commit }, sections) => commit('setActiveSections', sections),
    setSelectedSection: ({ commit }, sectionId) => commit('setSelectedSection', sectionId)
  },
  getters: {
    entities: state => state.entities,
    maps: state => state.maps,
    selectedEntityQID: state => state.selectedEntityQID,
    selectedMapID: state => state.selectedMapID,
    documentSections: state => state.documentSections,
    activeSections: state => state.activeSections,
    selectedSection: state => state.selectedSection
  },
  modules: {
  }
})
