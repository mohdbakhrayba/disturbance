<template lang="html">
    <div>

        <span class="row col-sm-12">
            <div class="col-sm-4 form-group">
                <label class="inline">Title:</label>
                <input
                    type="text"
                    class="form-control"
                    v-model="proposal.proposal_apiary.title"
                    :readonly="readonly"
                />
            </div>
        </span>

        <span class="row col-sm-12">
            Mark the location of the new proposed site either by entering the latitude and longitude or by clicking the location in the map.
        </span>

        <div class="row col-sm-12">
            <div class="col-sm-4 form-group">
                <label class="inline">Latitude:</label>
                <input
                    type="number"
                    min="-90"
                    max="90"
                    class="form-control"
                    v-model.number="proposal.proposal_apiary.latitude"
                    :readonly="readonly"
                />
            </div>
        </div>

        <div class="row col-sm-12">
            <div class="col-sm-4 form-group">
                <label class="inline">Longitude:</label>
                <input
                    type="number"
                    min="-180"
                    max="180"
                    class="form-control"
                    v-model.number="proposal.proposal_apiary.longitude"
                    :readonly="readonly"
                />
                <template v-if="!readonly">
                    <input type="button" @click="tryCreateNewSiteFromForm" value="Add proposed site" class="btn btn-primary">
                </template>
            </div>
        </div>

        <template v-if="proposal && proposal.proposal_apiary">
            <div class="row col-sm-12 debug-info">
                <div>
                    Category:
                    <select v-model="current_category" class="form-group">
                        <option value="south_west">South West</option>
                        <option value="remote">Remote</option>
                    </select>
                </div>

                Remainders:
                <div v-for="remainder in proposal.proposal_apiary.site_remainders" class="debug-remainders">
                    <div>
                        {{ remainder.category_name }}: {{ remainder.remainders }} left (${{ remainder.fee }}/site)
                    </div>
                </div>
            </div>
        </template>

        <div class="row col-sm-12">
            <datatable ref="site_locations_table" id="site-locations-table" :dtOptions="dtOptions" :dtHeaders="dtHeaders" />
        </div>

        <div id="map" class="map"></div>

        <div class="row col-sm-12">
            <label>
                Click <a @click="existingSiteAvailableClicked">here</a> if you are interested in existing sites that are available by the site licence holder.
            </label>
        </div>

        <SiteLocationsModal ref="site_locations_modal" />

    </div>
</template>

<script>
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
    //import geo_data from "../../../assets/apiary_data.json"
    import TextField from '@/components/forms/text.vue'
    import datatable from '@vue-utils/datatable.vue'
    import uuid from 'uuid';
    import SiteLocationsModal from './site_locations_modal';

    export default {
        props:{
            proposal:{
                type: Object,
                required:true
            },
            canEditActivities:{
              type: Boolean,
              default: true
            },
            is_external:{
              type: Boolean,
              default: false
            },
            is_internal:{
              type: Boolean,
              default: false
            },
            is_referral:{
              type: Boolean,
              default: false
            },
            hasReferralMode:{
                type:Boolean,
                default: false
            },
            hasAssessorMode:{
                type:Boolean,
                default: false
            },
            referral:{
                type: Object,
                required:false
            },
            proposal_parks:{
                type:Object,
                default:null
            },
        },
        data:function () {
            let vm=this;
            return{
                current_category: 'south_west',
                q: null,
                values:null,
                showingHelpText: false,
                help_text: 'My Help text ...',
                marker_lng: null,
                marker_lat: null,
                deed_poll_url: '',

                // variables for the GIS
                map: null,
                apiarySitesQuerySource: new VectorSource(),
                apiarySitesQueryLayer: null,
                bufferedSites: null,
                drawingLayerSource:  new VectorSource(),
                drawingLayer: null,
                bufferLayerSource: new VectorSource(),
                bufferLayer: null,
                existing_sites_feature_collection: null,
                //

                dtHeaders: [
                    'Id',
                    'Guid',
                    'Latitude',
                    'Longitude',
                    'Action',
                ],
                dtOptions: {
                    serverSide: false,
                    searchDelay: 1000,
                    lengthMenu: [ [10, 25, 50, 100, -1], [10, 25, 50, 100, "All"] ],
                    order: [
                        [0, 'desc']
                    ],
                    language: {
                        processing: "<i class='fa fa-4x fa-spinner fa-spin'></i>"
                    },
                    responsive: true,
                    processing: true,
                //    "id": '',
                //    "latitude": this.getDegrees(feature.getGeometry().getCoordinates()),
                //    "longitude": this.getDegrees(feature.getGeometry().getCoordinates()),
                //    "site_guid": feature.getId()
                    columns: [
                        {
                            visible: true,
                            mRender: function (data, type, full) {
                                if (full.id) {
                                    return full.id;
                                } else {
                                    return '';
                                }
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                if (full.getId()) {
                                    //return full.site_guid;
                                    return full.getId();
                                } else {
                                    return '';
                                }
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                let coords = full.getGeometry().getCoordinates()
                                return Number.parseFloat(coords[1]).toFixed(6)
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                let coords = full.getGeometry().getCoordinates()
                                return Number.parseFloat(coords[0]).toFixed(6)
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                let ret_str = ''
                                if (!vm.readonly){
                                    ret_str = '<span class="delete_button" style="color:#347ab7; cursor: pointer;" data-site-location-guid="' + full.getId() + '">Delete</span>'
                                }
                                return ret_str
                            }
                        },
                    ],
                },
            }
        },
        components: {
            TextField,
            datatable,
            SiteLocationsModal,
        },
        computed:{
            readonly: function() {
                let readonlyStatus = true;
                if (this.proposal.customer_status === 'Draft' && !this.is_internal) {
                    readonlyStatus = false;
                }
                return readonlyStatus;
            },
        },
        watch:{
        },
        methods:{
            uuidv4: function () {
                return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, 
                    function(c) {
                        return (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16);
                    }
                );
            },
            getDegrees: function(coords){
                return coords[0].toFixed(6) + ', ' + coords[1].toFixed(6);
            },
            metersToNearest: function(coords, filter) {
                // Infinity is the distance to the nearest apiary_site as default
                // Which means we it is fine to put apiary_site at the coords
                let candidates = [Number.POSITIVE_INFINITY];

                // Retrieve the nearest apiary site from the drawingLayerSource
                let nearestDrawnSite = this.drawingLayerSource.getClosestFeatureToCoordinate(coords, filter);
                if (nearestDrawnSite != null) {
                    candidates.push(getDistance(coords, nearestDrawnSite.getGeometry().getCoordinates()));
                }

                // Retrieve the nearest apiary site from the existing apiary_sites
                let nearestQuerySite = this.apiarySitesQuerySource.getClosestFeatureToCoordinate(coords, filter);
                if (nearestQuerySite != null) {
                    candidates.push(getDistance(coords, nearestQuerySite.getGeometry().getCoordinates()));
                }

                let min = candidates[0];
                for (let i = 1; i < candidates.length; i++) {
                    // Ignore NaN
                    if (!isNaN(candidates[i])){
                        min = Math.min(min, candidates[i]);
                    }
                }
                return min;
            },
            isNewPositionValid: function(coords){
                let distance = this.metersToNearest(coords, null);
                if (distance < 3000) {
                    console.log('distance: ' + distance + ' NG');
                    return false;
                }
                console.log('distance: ' + distance + ' OK');
                return true;
            },
            createBufferForSite: function(site){
                let id = site.getId() + "_buffer";
                let coords = site.getGeometry().getCoordinates();

                // apiary from json had 2d coords packed in an inner array.
                if (coords.length == 1){
                    coords = coords[0];
                }

                let buffer = new Feature(circular(coords, 3000, 16));
                buffer.setId(id)
                this.bufferLayerSource.addFeature(buffer);
            },
            removeBufferForSite: function(site){
                let buffer = this.bufferLayerSource.getFeatureById(site.getId() + "_buffer");
                this.bufferLayerSource.removeFeature(buffer);
            },
            existingSiteAvailableClicked: function() {
                alert("TODO: open screen 45: External - Contact Holder of Available Site in a different tab page.");
            },
            calculateRemainders: function(features){
                console.log('in calculateRemainders')
                let remainders = this.proposal.proposal_apiary.site_remainders
                let num_remain_south_west = 0
                let num_remain_remote = 0

                for (let i=0; i<remainders.length; i++){
                    if (remainders[i].category_name == 'South West'){
                        num_remain_south_west = remainders[i].remainders
                    } else if (remainders[i].category_name == 'Remote'){
                        num_remain_remote = remainders[i].remainders
                    } else {
                        console.log('should not reach here')
                    }
                }

                for (let i=0; i<features.length; i++){
                    if (features[i].get('site_category') == 'south_west'){
                        num_remain_south_west = num_remain_south_west - 1
                    } else if (features[i].get('site_category') == 'remote'){
                        num_remain_remote = num_remain_remote - 1
                    }
                }

                console.log('South West: ' + num_remain_south_west)
                console.log('Remote: ' + num_remain_remote)

                let button_text = 'Pay and submit'
                if (num_remain_south_west >= 0 && num_remain_remote >=0){
                    button_text = 'Submit'
                }

                console.log('emit!!!')
                this.$emit('button_text', button_text)
            },
            constructSiteLocationsTable: function(){
                console.log('in constructSiteLocationTable')

                if (this.drawingLayerSource){
                    // Clear table
                    this.$refs.site_locations_table.vmDataTable.clear().draw();

                    // Get all the features drawn
                    let features = this.drawingLayerSource.getFeatures()
                    console.log('features.length: ' + features.length)

                    // Insert data into the table
                    for(let i=0; i<features.length; i++){
                        this.$refs.site_locations_table.vmDataTable.row.add(features[i]).draw();
                        console.log('site_category: ' + features[i].get('site_category'));
                    }

                    this.calculateRemainders(features)
                }
                // Update proposal obj, which is sent to the server when save/submit.
                //this.proposal.proposal_apiary.apiary_sites = features
                //this.updateApiarySitesData()
            },
            getFeatures: function() {
                let allFeatures = this.drawingLayerSource.getFeatures()
                return allFeatures
            },
            addEventListeners: function(){
                $("#site-locations-table").on("click", ".delete_button", this.removeSiteLocation);
            },
            removeSiteLocation: function(e){
                console.log('removeSiteLocation')

                let site_location_guid = e.target.getAttribute("data-site-location-guid");
                console.log('guid to delete');
                console.log(site_location_guid);

                let myFeature = this.drawingLayerSource.getFeatureById(site_location_guid)

                // Remove buffer
                this.removeBufferForSite(myFeature)

                this.drawingLayerSource.removeFeature(myFeature);

                this.constructSiteLocationsTable();
            },
            initMap: function() {
                console.log('initMap start')
                let vm = this;

                vm.map = new Map({
                    layers: [
                        new TileLayer({
                            source: new OSM(),
                            opacity:0.5
                        })
                    ],
                    target: 'map',
                    view: new View({
                        center: [115.95, -31.95],
                        zoom: 7,
                        projection: 'EPSG:4326'
                    })
                });
                vm.apiarySitesQueryLayer = new VectorLayer({
                    source: vm.apiarySitesQuerySource,
                });
                vm.map.addLayer(vm.apiarySitesQueryLayer);

                vm.bufferedSites = [];
                vm.map.on("moveend", function(attributes){
                    console.log('moveend')

                    let zoom = vm.map.getView().getZoom();
                    console.log(zoom);
                    if (zoom < 11) {
                        return;
                    }

                    let fresh = 0;
                    let cached = 0;

                    vm.apiarySitesQuerySource.forEachFeatureInExtent(vm.map.getView().calculateExtent(), function(feature) {
                        let id = feature.getId();
                        if (vm.bufferedSites.indexOf(id) == -1) {
                            vm.createBufferForSite(feature);
                            vm.bufferedSites.push(id);
                            fresh++;
                        }
                        else {
                            cached++;
                        }
                    });

                    console.log("zoom: " + zoom + ", fresh: " + fresh + ", cached: " + cached);
                });

                // In memory vector layer for digitization
                //vm.drawingLayerSource = new VectorSource();
                vm.drawingLayerSource.on('addfeature', function(e){
                    console.log('in addfeature')
                    console.log(e.feature)
                    //vm.proposal.proposal_apiary.apiary_sites.push(e.feature)
                    vm.constructSiteLocationsTable()
                });
                vm.drawingLayer = new VectorLayer({
                    source: vm.drawingLayerSource,
                    style: new Style({
                        fill: new Fill({
                            color: 'rgba(255, 255, 255, 0.2)'
                        }),
                        stroke: new Stroke({
                            color: '#ffcc33',
                            width: 2
                        }),
                        image: new CircleStyle({
                            radius: 7,
                            fill: new Fill({
                                color: '#ffcc33'
                            })
                        })
                    })
                });
                vm.map.addLayer(vm.drawingLayer);

                // In memory vector layer for buffer

                //vm.bufferLayerSource = new VectorSource();
                vm.bufferLayer = new VectorLayer({
                    source: vm.bufferLayerSource,
                    minZoom: 11,

                });
                vm.map.addLayer(vm.bufferLayer);

                // Full screen toggle
                vm.map.addControl(new FullScreenControl());

                // Show mouse coordinates
                vm.map.addControl(new MousePositionControl({
                    coordinateFormat: function(coords){
                        let message = vm.getDegrees(coords) + "\n";
                        let distance = vm.metersToNearest(coords, null);
                        if (distance < Number.POSITIVE_INFINITY) {
                            message += "<br>Nearest: "  + (distance / 1000).toFixed(2) + " km";
                        }
                        return  message;
                    },
                    target: document.getElementById('mouse-position'),
                    className: 'custom-mouse-position',
                }));

                // Draw and modify tools
                if (!vm.readonly){
                    let modifyInProgressList = [];
                    let drawTool = new Draw({
                        source: vm.drawingLayerSource,
                        type: "Point"
                    });
                    drawTool.on("drawstart", function(attributes){
                        console.log('drawstart')

                        if (!vm.isNewPositionValid(attributes.feature.getGeometry().getCoordinates())) {
                            drawTool.abortDrawing();
                        }
                    });
                    drawTool.on('drawend', function(attributes){
                        console.log('drawend')

                        if (!this.readoly){
                            let feature = attributes.feature;
                            feature.setId(vm.uuidv4());
                            feature.set("source", "draw");
                            feature.set('site_category', vm.current_category) // For now, we add category, either south_west/remote to the feature 
                                                                              //according to the selection of the UI
                            feature.getGeometry().on("change", function() {
                                console.log("Start Modify feature: " + feature.getId());

                                if (modifyInProgressList.indexOf(feature) < 0) {
                                    modifyInProgressList.push(feature);
                                }
                            });
                            vm.createBufferForSite(feature);
                            // Vue table is updated by the event 'addfeature' issued from the Source
                        }
                    });
                    vm.map.addInteraction(drawTool);

                    let modifyTool = new Modify({
                        source: vm.drawingLayerSource,
                    });
                    //modifyTool.on("modifystart", function(attributes){
                    //    console.log('modifystart')
                    //    console.log(attributes)
                    //});
                    modifyTool.on("modifyend", function(attributes){
                        console.log('modifyend')
                        // this will list all features in layer, not so useful without cross referencing
                        attributes.features.forEach(function(feature){
                            let index = modifyInProgressList.indexOf(feature);
                            if (index > -1) {
                                console.log("End Modify Feature: " + index + "/" + modifyInProgressList.length + " " + feature.getId());

                                let coords = feature.getGeometry().getCoordinates()
                                console.log(coords)
                                //let valid = vm.isNewPositionValid(coords, function(fe){
                                //    console.log('filter function')
                                //    console.log(fe)
                                //    return true
                                //})
                                let valid = vm.isNewPositionValid(coords, vm.excludeFeature)
                                console.log(valid)

                                modifyInProgressList.splice(index, 1);
                                //vm.updateVueFeature(feature);
                                vm.removeBufferForSite(feature);
                                vm.createBufferForSite(feature);

                                vm.constructSiteLocationsTable()
                            }
                        });
                    });
                    vm.map.addInteraction(modifyTool);
                }
                console.log('initMap end')
            },  // End: initMap()
            excludeFeature: function(f) {
                console.log('in excludeFeature')
                console.log('TODO: implement this function')
                console.log(f)
                return true
            },
            tryCreateNewSiteFromForm: function(){
                console.log('in tryCreateNewSiteFromForm')

                let lat = this.proposal.proposal_apiary.latitude
                let lon = this.proposal.proposal_apiary.longitude
                // rough bounding box for preliminary check
                if (isNaN(lon) || lon < 112 || lon > 130 ||
                    isNaN(lat) || lat < -35 || lat > -11) {
                    return false;
                }
                if(!this.isNewPositionValid([lon,lat]))
                {
                    return false;
                }
                let feature = new Feature(new Point([lon,lat]));
                feature.setId(this.uuidv4());
                feature.set("source", "form");
                feature.set('site_category', this.current_category) // For now, we add category, either south_west/remote to the feature according to the selection of the UI
                this.drawingLayerSource.addFeature(feature);

                console.log('new feature added to the layer')

                this.createBufferForSite(feature);
                return true;
            },
        },
        created: function() {
            console.log('created start')
            let vm = this
            this.$http.get('/api/apiary_site/list_existing/?proposal_id=' + this.proposal.id)
            .then(
                res => {
                    console.log('existing: ')
                    console.log(res.body)
                    vm.existing_sites_feature_collection = res.body
                    vm.apiarySitesQuerySource.addFeatures((new GeoJSON()).readFeatures(vm.existing_sites_feature_collection))
                },
                err => {

                }
            )
            console.log('created end')
        },
        mounted: function() {
            console.log('mounted start')
            let vm = this;

            this.$nextTick(() => {
                vm.initMap();
                vm.addEventListeners();
            });

            // Create feature and add it to the map, then reconstruct table
            // Don't forget add 'id' field to the feature which is used to determine if it is new feature or not
            console.log('apiary_sites.length: ')
            console.log(vm.proposal.proposal_apiary.apiary_sites.length)

            for (let i=0; i<vm.proposal.proposal_apiary.apiary_sites.length; i++){
                 let apiary_site = vm.proposal.proposal_apiary.apiary_sites[i]

                 console.log('apiary_site')
                 console.log(apiary_site)

                 let feature = new Feature(new Point([apiary_site.coordinates.lng, apiary_site.coordinates.lat]));
                 feature.setId(apiary_site.site_guid);
                 feature.id = apiary_site.id
                 feature.set("source", "form");
                 feature.set("site_category", apiary_site.site_category)
                 this.drawingLayerSource.addFeature(feature);

                 console.log('new feature added to the layer')

                 this.createBufferForSite(feature);
            }

            this.constructSiteLocationsTable();
            console.log('mounted end')
        }
    }
</script>

<style lang="css">
    .delete_button {
        color: #337ab7 !important;
    }
    .section{
        text-transform: capitalize;
    }
    .list-group{
        margin-bottom: 0;
    }
    .fixed-top{
        position: fixed;
        top:56px;
    }
    .debug-info {
        background: #CCC;
        padding: 1em;
        margin: 1em;
    }
    .debug-message {
        margin: 0 0 1em 0;
        padding: 0 0 0 1em
    }
    .debug-remainders {
        padding: 0 0 0 1em
    }
    .map {
        display: inline-block;
        width: 100%;
        height: 500px;
    }
    .custom-mouse-position {
        position: absolute;
        bottom: 16px;
        left: 16px;
        top: auto;
        right: auto;
        text-align: left;
        font-size: 0.8rem;
        border: 0;
        padding: 8px;
        color: white;
        background-color: rgba(37, 45, 51, 0.7);
    }
</style>
