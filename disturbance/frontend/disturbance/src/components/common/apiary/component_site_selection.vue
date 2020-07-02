<template lang="html">
    <div>

        <div class="row col-sm-12">
            <div class="col-sm-6">
                <datatable
                    ref="table_apiary_site"
                    :id="table_id"
                    :dtOptions="dtOptions"
                    :dtHeaders="dtHeaders"
                />
                <template v-if="show_view_all_features_button">
                    <div class="button_row">
                        <span class="view_all_button" @click="displayAllFeatures">View All On Map</span>
                    </div>
                </template>
            </div>

            <div class="col-sm-6">
                <ComponentMap 
                    ref="component_map"
                    :apiary_site_geojson_array="apiary_site_geojson_array"
                    :key="component_map_key"
                />
            </div>
        </div>

    </div>
</template>

<script>
    import Vue from 'vue'
    import datatable from '@vue-utils/datatable.vue'
    import uuid from 'uuid'
    import ComponentMap from '@/components/common/apiary/component_map.vue'

    export default {
        props:{
            apiary_sites: {
                type: Array,
                default: function(){
                    return [];
                }
            },
            is_external:{
                type: Boolean,
                default: false,
            },
            is_internal:{
                type: Boolean,
                default: false,
            },
            show_col_id: {
                type: Boolean,
                default: false,
            },
            show_col_checkbox: {
                type: Boolean,
                default: true,
            },
            enable_col_checkbox: {
                type: Boolean,
                default: true,
            },
            show_col_site: {
                type: Boolean,
                default: true,
            },
            show_col_longitude: {
                type: Boolean,
                default: false,
            },
            show_col_latitude: {
                type: Boolean,
                default: false,
            },
            show_col_district: {
                type: Boolean,
                default: false,
            },
            show_col_status: {
                type: Boolean,
                default: false,
            },
            show_col_previous_site_holder: {
                type: Boolean,
                default: false,
            },
            show_col_action: {
                type: Boolean,
                default: true,
            },
            show_view_all_features_button: {
                type: Boolean,
                default: true,
            }
        },
        watch: {

        },
        data: function(){
            let vm = this;
            return{
                apiary_sites_local: JSON.parse(JSON.stringify(this.apiary_sites)),  // Deep copy the array
                component_map_key: '',
                table_id: uuid(), 
                apiary_site_geojson_array: [],  // This is passed to the ComponentMap as props
                default_checkbox_checked: false,  // If checked property isn't set as a apiary_site's property, this default value is used
                dtHeaders: [
                    'Id',
                    'C',
                    'Site',
                    'Longitude',
                    'Latitude',
                    'District',
                    'Status',
                    'Previous Site Holder/Applicant',
                    'Action',
                ],
                dtOptions: {
                    serverSide: false,
                    searchDelay: 1000,
                    lengthMenu: [ [10, 25, 50, 100, -1], [10, 25, 50, 100, "All"] ],
                    order: [
                        [1, 'desc'], [0, 'desc'],
                    ],
                    language: {
                        processing: "<i class='fa fa-4x fa-spinner fa-spin'></i>"
                    },
                    responsive: true,
                    processing: true,
                    columns: [
                        {
                            // Id (database id)
                            visible: vm.show_col_id,
                            mRender: function (data, type, apiary_site) {
                                return apiary_site.id;
                            }
                        },
                        {
                            // Checkbox
                            visible: vm.show_col_checkbox,
                            className: 'dt-body-center',
                            mRender: function (data, type, apiary_site) {
                                let disabled_str = ''
                                if (!vm.enable_col_checkbox){
                                    disabled_str = ' disabled '
                                }
                                if (apiary_site.checked){
                                    return '<input type="checkbox" class="site_checkbox" data-apiary-site-id="' + apiary_site.id + '"' + disabled_str + ' checked/>'
                                } else {
                                    return '<input type="checkbox" class="site_checkbox" data-apiary-site-id="' + apiary_site.id + '"' + disabled_str + '/>'
                                }
                            }
                        },
                        {
                            // Site
                            visible: vm.show_col_site,
                            mRender: function (data, type, apiary_site) {
                                return 'site:' + apiary_site.id
                            }
                        },
                        {
                            // Longitude
                            visible: vm.show_col_longitude,
                            mRender: function (data, type, apiary_site){
                                return 'lng'
                            }
                        },
                        {
                            // Latitude
                            visible: vm.show_col_latitude,
                            mRender: function (data, type, apiary_site){
                                return 'lat'
                            }
                        },
                        {
                            // District
                            visible: vm.show_col_district,
                            mRender: function (data, type, apiary_site){
                                return 'dist'
                            }
                        },
                        {
                            // Status
                            visible: vm.show_col_status,
                            mRender: function (data, type, apiary_site){
                                return 'status'
                            }
                        },
                        {
                            // Previous Site Holder/Applicant
                            visible: vm.show_col_previous_site_holder,
                            mRender: function (data, type, apiary_site){
                                return 'holder'
                            }
                        },
                        {
                            // Action
                            mRender: function (data, type, apiary_site) {
                                //let ret = '<a><span class="view_on_map" data-apiary-site-id="' + apiary_site.id + '"/>View on Map</span></a>';
                                //return ret;

                                let action_list = []

                                // View on map
                                let view_on_map_html = '<a><span class="view_on_map" data-apiary-site-id="' + apiary_site.id + '"/>View on map</span></a>';
                                action_list.push(view_on_map_html);

                                // Mark as Available/Unavailable
                                let display_text = ''
                                if (vm.is_external){
                                    if (apiary_site.available){
                                        display_text = 'Mark as unavailable';
                                    } else {
                                        display_text = 'Mark as available';
                                    }
                                    let ret = '<a><span class="toggle_availability" data-apiary-site-id="' + apiary_site.id + 
                                        '" data-apiary-site-available="' + apiary_site.available + '"/>' + display_text + '</span></a>';
                                    action_list.push(ret);
                                } else if (vm.is_internal){
                                    if (apiary_site.available){
                                        display_text = 'Available';
                                    } else {
                                        display_text = 'Unavailable';
                                    }
                                    action_list.push(display_text);
                                }
                                return action_list.join('<br />');
                            }
                        },
                    ],
                },
            }
        },
        created: function(){

        },
        mounted: function(){
            let vm = this;
            this.$nextTick(() => {
                vm.addEventListeners();
                vm.constructApiarySitesTable();
                vm.addApiarySitesToMap(vm.apiary_sites)
                vm.ensureCheckedStatus();
            });
            this.$emit('apiary_sites_updated', this.apiary_sites_local)
        },
        components: {
            ComponentMap,
            datatable,
        },
        computed: {

        },
        methods: {
            ensureCheckedStatus: function() {
                console.log('in ensureCheckedStatus')
                if (this.apiary_sites.length > 0){
                    for(let i=0; i<this.apiary_sites.length; i++){
                        if (!this.apiary_sites[i].hasOwnProperty('checked')){
                            this.apiary_sites[i].checked = this.default_checkbox_checked
                        }
                    }
                }
            },
            forceToRefreshMap: function() {
                console.log('forceToRefreshMap in component_site_selection.vue')
                if (this.$refs.component_map){
                    this.$refs.component_map.forceToRefreshMap()
                }
            },
            displayAllFeatures: function(){
                if (this.$refs.component_map){
                    this.$refs.component_map.displayAllFeatures()
                }
            },
            addApiarySitesToMap: function(apiary_sites) {
                console.log('in addApiarySitesToMap')
                for (let i=0; i<apiary_sites.length; i++){
                    console.log(apiary_sites[i])
                    if (apiary_sites[i].hasOwnProperty('checked')){
                        //apiary_sites[i].as_geojson['properties']['checked'] = apiary_sites[i].checked
                        apiary_sites[i].as_geojson.properties.checked = apiary_sites[i].checked
                    }
                    this.apiary_site_geojson_array.push(apiary_sites[i].as_geojson)
                }

                // Reload ComponentMap by assigning a new key value
                this.component_map_key = uuid()
            },
            constructApiarySitesTable: function() {
                if (this.$refs.table_apiary_site){
                    // Clear table
                    this.$refs.table_apiary_site.vmDataTable.clear().draw();

                    // Construct table
                    if (this.apiary_sites.length > 0){
                        for(let i=0; i<this.apiary_sites.length; i++){
                            this.addApiarySiteToTable(this.apiary_sites[i]);
                        }
                    }
                }
            },
            addApiarySiteToTable: function(apiary_site) {
                this.$refs.table_apiary_site.vmDataTable.row.add(apiary_site).draw();
            },
            addEventListeners: function () {
                $("#" + this.table_id).on("click", ".view_on_map", this.zoomOnApiarySite)
                $("#" + this.table_id).on("click", ".toggle_availability", this.toggleAvailability)
                $("#" + this.table_id).on('click', 'input[type="checkbox"]', this.checkboxClicked)
            },
            updateApiarySite: function(site_updated) {
                // Update internal apiary_site data
                for (let i=0; i<this.apiary_sites.length; i++){
                    if (this.apiary_sites[i].id == site_updated.id){
                        this.apiary_sites[i].available = site_updated.available
                    }
                }
            },
            checkboxClicked: function(e) {
                let vm = this;
                let apiary_site_id = e.target.getAttribute("data-apiary-site-id");
                let checked_status = e.target.checked
                for (let i=0; i<this.apiary_sites_local.length; i++){
                    if (this.apiary_sites_local[i].id == apiary_site_id){
                        this.apiary_sites_local[i].checked = checked_status
                    }
                }
                this.$emit('apiary_sites_updated', this.apiary_sites_local)
                this.$refs.component_map.setApiarySiteSelectedStatus(apiary_site_id, checked_status)
            },
            toggleAvailability: function(e) {
                let vm = this;
                let apiary_site_id = e.target.getAttribute("data-apiary-site-id");
                let current_availability = e.target.getAttribute("data-apiary-site-available");
                let requested_availability = current_availability === 'true' ? false : true

                vm.$http.patch('/api/apiary_site/' + apiary_site_id + '/', { 'available': requested_availability }).then(
                    async function(accept){
                        // Update the site in the table
                        let site_updated = accept.body
                        this.updateApiarySite(site_updated)
                        vm.constructApiarySitesTable();
                    },
                    reject=>{
                        swal(
                            'Submit Error',
                            helpers.apiVueResourceError(err),
                            'error'
                        )
                    }
                );
            },
            zoomOnApiarySite: function(e) {
                console.log(e)
                let apiary_site_id = e.target.getAttribute("data-apiary-site-id");
                this.$refs.component_map.zoomToApiarySiteById(apiary_site_id)
            },
        },
    }
</script>

<style lang="css" scoped>
.component-site-selection {
    border: solid 2px #5BB;
}
.button_row {
    display: flex;
    justify-content: flex-end;
}
.view_all_button {
    color: #03a9f4;
    cursor: pointer;
}
.site_checkbox {
    text-align: center;
}
</style>
