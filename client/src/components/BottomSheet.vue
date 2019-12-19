<template>
  <div tabindex="-1" class="v-dialog__content v-dialog__content--active">
    <transition name="bottom-sheet-transition">
      <div class="v-dialog v-bottom-sheet v-dialog--active v-dialog--persistent" v-if="show">
        <v-card
          class="mx-auto"
        >
          <v-card-actions>
            <v-btn @click="toggleBottomSheetIsVisible" text>Close</v-btn>
          </v-card-actions>

          <v-card-title class="text-center">
          </v-card-title>

          <v-card-text class="text-left">
            <lmap
              :center="[38.895, -77.036667]"
              :zoom="11"
            />
          </v-card-text>

        </v-card>      
      </div>
    </transition>
  </div>
</template>

<script>
  import Map from './Map'

  export default {
    name: 'BottomSheet',
    components: {
      lmap: Map
    },
    data: () => ({
      show: false
    }),
    computed: {
      activeSections() { return this.$store.getters.activeSections },
      activeSection() { return this.activeSections.length > 0 ? this.activeSections[0] : null }
    },
    mounted() {
      console.log('BottomSheet.mounted')
      for (let i = 1; i < 9; i++) {
        document.body.querySelectorAll(`h${i}`).forEach((heading) => {
          heading.addEventListener('click', this.toggleBottomSheetIsVisible)
        })
      }
    },
    methods: {
      toggleBottomSheetIsVisible() {
        this.show = !this.show
      }
    },
    watch: {
      activeSection(sectionId) {
        console.log(`BottomSheet.activeSection=${sectionId}`)
      }
    }
  }
</script>

<style>

  #details {
    margin: 0 15px;
    z-index: 10;
  }
  
  .v-bottom-sheet.v-dialog {
    height: 50%;
    background: white;
  }

</style>

