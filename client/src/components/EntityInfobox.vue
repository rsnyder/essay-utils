<template>
  <div>
    <v-dialog v-model="isOpen" @click:outside="setSelectedEntityQID(null)" width="500">
      <v-card v-if="entityInfo">
        <v-card-title class="headline grey lighten-2" primary-title v-html="entityInfo.displaytitle"/>
        <v-card-text>
          <img :src="entityInfo.thumbnail.source">
          <div class="subtitle">{{ entityInfo.description }}</div>
          <div v-html="entityInfo.extract_html"/>
        </v-card-text>
        <v-divider/>
        <v-card-actions>
          <v-spacer/>
          <v-btn color="primary" text @click="setSelectedEntityQID(null)">Dismiss</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>

export default {
  name: 'entity-infobox',
  data: () => ({
    isOpen: false
  }),
  computed: {
    entities () { return this.$store.state.entities },
    selectedEntityQID () { return this.$store.state.selectedEntityQID },
    entity() { return this.entities[this.selectedEntityQID] || {} },
    entityInfo() { return this.entity['wikipedia summary'] },
    imageSrc() { return this.entity.images ? this.entity.images[0] : '' }
  },
  methods: {
    setSelectedEntityQID(arg) {
      const qid = arg && arg.target ? arg.target.attributes['data-qid'].value : arg
      const selectedEntity = qid === this.selectedEntityQID ? null : qid
      this.$store.dispatch('setSelectedEntityQID', selectedEntity)
    }
  },
  watch: {
    selectedEntityQID(qid) {
      this.isOpen = qid !== null
    }
  }
}
</script>

<style scoped>

  img {
    /* object-fit:
       fill = stretched to fit box
       contain = maintain its aspect ratio, scaled fit within the element’s box, letterboxed if needed
       cover = fills entire box, maintains aspect ration, clipped to fit
       none = content not resized
       scale-down = same as none or contain, whichever is smaller
    */
    object-fit: contain; 
    width: 150px;
    height: 150px;
    padding: 2px 10px 2px 0;
    float: left;
    vertical-align: top;
  }

  .subtitle {
    line-height: 1em;
    margin-bottom: 8px;
    font-weight: bold;
    font-size: 1.1em;
  }

</style>
