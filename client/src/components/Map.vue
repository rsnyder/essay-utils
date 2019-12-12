<template>
    <div class="row wrapper">
        <div class="col-md-9">
            <div id="map" class="lmap"></div>
        </div>
        <div class="col-md-3">
            <div
                class="form-check"
                v-for="layer in layers"
                :key="layer.id"
            >
                <label class="form-check-label">
                <input
                    class="form-check-input"
                    type="checkbox"
                    v-model="layer.active"
                    @change="layerChanged(layer.id, layer.active)"
                />
                    {{ layer.name }}
                </label>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'Map',
    props: {
        mapid: { type: String, default: 'map-1' },
        center: { type: Array, default: function () { return [] } },
        zoom: { type: Number, default: 10 },
        width: { type: String, default: '400px' },
        height: { type: String, default: '400px' }
    },
    data: () => ({
        map: null,
        tileLayer: null,
        layers: [
            {
                id: 0,
                name: 'locations',
                active: false,
                features: []
            }
        ]
    }),
    computed: {
        entities() { return this.$store.state.entities },
        locations() { return Object.values(this.entities).filter(entity => entity.coords) }
    },
    mounted() {
        console.log(`map.mounted: mapid=${this.mapid} center=${this.props} zoom=${this.zoom} width=${this.width} height=${this.height}`)
        console.log(this)
        this.initMap()
        this.initLayers()
    },
    methods: {
        initMap() {
            this.map = this.$L.map('map').setView(this.center, this.zoom)
            this.tileLayer = this.$L.tileLayer(
                'https://cartodb-basemaps-{s}.global.ssl.fastly.net/rastertiles/voyager/{z}/{x}/{y}.png',
                {
                    maxZoom: 18,
                    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attribution">CARTO</a>'
                }
            )
            this.tileLayer.addTo(this.map)
        },
        initLayers() {
            this.layers.filter(layer => layer.name === 'locations').forEach((markerLayer) => {
                let i = 0
                this.locations.forEach((location) => {
                    const feature = {
                        id: i++,
                        name: location.label,
                        type: 'marker',
                        coords: location.coords[0]
                    }
                    feature.leafletObject = this.$L.marker(feature.coords).bindPopup(feature.name)
                    markerLayer.features.push(feature)
                })
                console.log('markerLayer', markerLayer)
            })
            /*
            this.layers.forEach((layer) => {
                const markerFeatures = layer.features.filter(feature => feature.type === 'marker')
                markerFeatures.forEach((feature) => {
                    feature.leafletObject = this.$L.marker(feature.coords)
                    .bindPopup(feature.name);
                })
                const polygonFeatures = layer.features.filter(feature => feature.type === 'polygon')
                polygonFeatures.forEach((feature) => {
                    feature.leafletObject = this.$L.polygon(feature.coords)
                    .bindPopup(feature.name);
                })
            })
            */
        },
        layerChanged(layerId, active) {
            const layer = this.layers.find(layer => layer.id === layerId)
            layer.features.forEach((feature) => {
                if (active) {
                    feature.leafletObject.addTo(this.map)
                } else {
                    feature.leafletObject.removeFrom(this.map)
                }
            })
        }
    }
}
</script>

<style>

    .wrapper {
        display: inherit;
    }
  
    .lmap {
        height: 400px;
        width: 400px;
    }

</style>
