<template>
  <div>
      <!-- This will be the popover target (for the events and position) -->
      <button @click="setSetSelectedEntity('Q123')">Click me</button>

    <v-popover
      show=isOpen,
      ref="popover"
      offset="16"
    >
      <!-- This will be the content of the popover -->
      <template slot="popover">
        <input class="tooltip-content" v-model="selectedEntity" placeholder="Tooltip content" />
        <p>
          {{ selectedEntity }}
        </p>

        <!-- You can put other components too
        <ExampleComponent char="=" /> -->
      </template>
    </v-popover>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'entity-infobox',
  data: () => ({
    isOpen: true
  }),
  computed: {
    entities () { return this.$store.state.entities },
    selectedEntity () { return this.$store.state.selectedEntity },
    entity() { return this.selectedEntity ? this.entities[this.selectedEntity] : {} }
  },
  watch: {
    selectedEntity(qid) {
      console.log(`selectedEntity=${qid} popoverIsEnabled=${qid !== null}`)
      this.$refs.popover.open = qid !== null
    }
  },
  methods: {
    setSetSelectedEntity(qid) {
      qid = qid === this.selectedEntity
        ? null
        : qid
      console.log(`setSetSelectedEntity=${qid}`)
      this.$store.dispatch('setSelectedEntity', qid)
    }
  }
}
</script>

<style></style>
