<template>
  <div>
    <v-dialog v-model="isOpen" width="500">
      <v-card>
        <v-card-title class="headline grey lighten-2" primary-title>
          {{ entity.label }}
        </v-card-title>
        <v-card-text>
          {{ entity.description }}
        </v-card-text>
        <v-divider/>
        <v-card-actions>
          <v-spacer/>
          <v-btn color="primary" text @click="setSetSelectedEntity(null)">Dismiss</v-btn>
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
    selectedEntity () { return this.$store.state.selectedEntity },
    entity() {
      return this.selectedEntity && this.entities[this.selectedEntity]
        ? this.entities[this.selectedEntity]
        : {}
      }
    },
  methods: {
    setSetSelectedEntity(arg) {
      const qid = arg && arg.target ? arg.target.attributes['data-qid'].value : arg
      const selectedEntity = qid === this.selectedEntity ? null : qid
      console.log(`setSetSelectedEntity=${selectedEntity}`)
      this.$store.dispatch('setSelectedEntity', selectedEntity)
    }
  },
  watch: {
    selectedEntity(qid) {
      this.isOpen = qid !== null
    }
  }
}
</script>

<style></style>
