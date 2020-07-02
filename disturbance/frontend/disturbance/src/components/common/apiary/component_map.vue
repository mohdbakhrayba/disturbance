<template lang="html">
    <div>
        <div :id="elem_id" class="map"></div>
        <div :id="popup_id" class="ol-popup">
            <a href="#" :id="popup_closer_id" class="ol-popup-closer"></a>
            <div :id="popup_content_id"></div>
        </div>
    </div>
</template>

<script>
    import uuid from 'uuid';
    import 'ol/ol.css';
    //import 'index.css';  // copy-and-pasted the contents of this file at the <style> section below in this file

    import Map from 'ol/Map';
    import View from 'ol/View';
    import WMTSCapabilities from 'ol/format/WMTSCapabilities';
    import TileLayer from 'ol/layer/Tile';
    import OSM from 'ol/source/OSM';
    import WMTS, {optionsFromCapabilities} from 'ol/source/WMTS';
    import Collection from 'ol/Collection';
    import {Draw, Modify, Snap} from 'ol/interaction';
    import VectorLayer from 'ol/layer/Vector';
    import VectorSource from 'ol/source/Vector'; 
    import {Circle as CircleStyle, Fill, Stroke, Style} from 'ol/style';
    import {FullScreen as FullScreenControl, MousePosition as MousePositionControl} from 'ol/control';
    import Vue from 'vue/dist/vue';
    import { Feature } from 'ol';
    import { Point } from 'ol/geom';
    import { getDistance } from 'ol/sphere';
    import { circular} from 'ol/geom/Polygon';
    import GeoJSON from 'ol/format/GeoJSON';

    export default {
        props:{
            is_external:{
                type: Boolean,
                default: false
            },
            is_internal:{
                type: Boolean,
                default: false
            },
            apiary_site_geojson_array: {
                type: Array,
                default: function(){
                    return []
                }
            },
        },
        watch: {

        },
        data: function(){
            return{
                map: null,
                apiarySitesQuerySource: null,
                apiarySitesQueryLayer: null,
                elem_id: uuid(),
                popup_id: uuid(),
                popup_closer_id: uuid(),
                popup_content_id: uuid(),
                style_not_checked: 
                    new Style({
                        image: new CircleStyle({
                            radius: 7,
                            fill: new Fill({color: '#e0e0e0'}),
                            stroke: new Stroke({color: '#616161', width: 2})
                        })
                    }),
                style_checked:
                    new Style({
                        image: new CircleStyle({
                        radius: 7,
                        fill: new Fill({color: '#03a9f4'}),
                        stroke: new Stroke({color: '#2e6da4', width: 2})
                        })
                    }),
            }
        },
        created: function(){

        },
        mounted: function(){
            let vm = this;
            this.$nextTick(() => {
                vm.addEventListeners()
            });
            this.initMap()
            this.displayAllFeatures()
        },
        components: {

        },
        computed: {

        },
        methods: {
            forceToRefreshMap: function() {
                let vm = this
                setTimeout(function(){
                    console.log('updateResize()')
                    vm.map.updateSize();
                }, 50)
            },
            initMap: function() {
                let vm = this;

                vm.map = new Map({
                    layers: [
                        new TileLayer({
                            source: new OSM(),
                            opacity:0.5
                        })
                    ],
                    //target: 'map',
                    target: vm.elem_id,
                    view: new View({
                        center: [115.95, -31.95],
                        zoom: 7,
                        projection: 'EPSG:4326'
                    })
                });
                vm.apiarySitesQuerySource = new VectorSource({

                });
                vm.apiarySitesQueryLayer = new VectorLayer({
                    source: vm.apiarySitesQuerySource,
                    //style: new Style({
                    //    fill: new Fill({
                    //        color: 'rgba(255, 255, 255, 0.2)'
                    //    }),
                    //    stroke: new Stroke({
                    //        color: '#ffcc33',
                    //        width: 2
                    //    }),
                    //    image: new CircleStyle({
                    //        radius: 7,
                    //        fill: new Fill({
                    //            color: '#ffcc33'
                    //        })
                    //    })
                    //})
                });
                vm.map.addLayer(vm.apiarySitesQueryLayer);

                // Full screen toggle
                vm.map.addControl(new FullScreenControl());

                // Show mouse coordinates
                vm.map.addControl(new MousePositionControl({
                    coordinateFormat: function(coords){
                        let message = vm.getDegrees(coords) + "\n";
                        return  message;
                    },
                    target: document.getElementById('mouse-position'),
                    className: 'custom-mouse-position',
                }));

                // Add apiary_sites passed as a props
                for (let i=0; i<vm.apiary_site_geojson_array.length; i++){
                    this.addApiarySite(vm.apiary_site_geojson_array[i])
                }
            },
            getDegrees: function(coords){
                return coords[0].toFixed(6) + ', ' + coords[1].toFixed(6);
            },
            // This function is not used
            getFillColour: function(status){
                switch(status){
                    case 'draft':
                        return new Fill({color: '#e0e0e0'})
                    case 'pending':
                        return new Fill({color: '#e0e0e0'})
                    case 'current':
                        return new Fill({color: '#e0e0e0'})
                    case 'suspended':
                        return new Fill({color: '#e0e0e0'})
                    case 'not_to_be_reissued':
                        return new Fill({color: '#e0e0e0'})
                    case 'denied':
                        return new Fill({color: '#e0e0e0'})
                    case 'vacant':
                        return new Fill({color: '#e0e0e0'})
                }
            },
            // This function is not used
            getStrokeColour: function(status){
                switch(status){
                    case 'draft':
                        return new Stroke({color: '#616161', width: 2})
                    case 'pending':
                        return new Stroke({color: '#616161', width: 2})
                    case 'current':
                        return new Stroke({color: '#616161', width: 2})
                    case 'suspended':
                        return new Stroke({color: '#616161', width: 2})
                    case 'not_to_be_reissued':
                        return new Stroke({color: '#616161', width: 2})
                    case 'denied':
                        return new Stroke({color: '#616161', width: 2})
                    case 'vacant':
                        return new Stroke({color: '#616161', width: 2})
                }
            },
            addApiarySite: function(apiary_site_geojson) {
                console.log('in addApiarySite')
                console.log(apiary_site_geojson)
                
                let feature = (new GeoJSON()).readFeature(apiary_site_geojson)
                let status = feature.get('status')
                let checked_status = apiary_site_geojson.properties.hasOwnProperty('checked') ? apiary_site_geojson.properties.checked : false
                console.log(checked_status)
                let style_applied = checked_status ? this.style_checked : this.style_not_checked
                feature.setStyle(style_applied)
                this.apiarySitesQuerySource.addFeature(feature)
            },
            zoomToApiarySiteById: function(apiary_site_id){
                let feature = this.apiarySitesQuerySource.getFeatureById(apiary_site_id)
                this.map.getView().animate({zoom: 10, center: feature['values_']['geometry']['flatCoordinates']})
            },
            setApiarySiteSelectedStatus: function(apiary_site_id, selected) {
                let feature = this.apiarySitesQuerySource.getFeatureById(apiary_site_id)
                let style_applied = selected ? this.style_checked : this.style_not_checked
                feature.setStyle(style_applied)
            },
            addEventListeners: function () {

            },
            displayAllFeatures: function() {
                if (this.apiarySitesQuerySource.getFeatures().length>0){
                    let view = this.map.getView()

                    let ext = this.apiarySitesQuerySource.getExtent()
                    let centre = [(ext[0] + ext[2])/2.0, (ext[1] + ext[3])/2.0]
                    //view.fit(ext)
                    let resolution = view.getResolutionForExtent(ext);
                    let z = view.getZoomForResolution(resolution) - 1
                    view.animate({zoom: z, center: centre})
                }
            },
        },
    }
</script>

<style lang="css" scoped>
</style>
