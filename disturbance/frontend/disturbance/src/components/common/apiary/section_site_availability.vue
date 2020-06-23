<template lang="html">
    <div class="row col-sm-12">
        <div class="row col-sm-12">
            <template v-if="is_external">
                <!--button v-if="!creatingProposal" class="btn btn-primary pull-right" @click="openNewTemporaryUse">Site Transfer</button-->
                <button 
                    class="btn btn-primary pull-right" 
                    @click="openNewSiteTransfer">
                    Site Transfer
                </button>
            </template>
        </div>
        <div class="col-sm-6">
            <datatable
                ref="site_availability_table"
                id="site-availability-table"
                :dtOptions="dtOptions"
                :dtHeaders="dtHeaders"
            />
        </div>
        <div class="col-sm-6">
            <ComponentMap 
                ref="component_map"
                :apiary_site_geojson_array="apiary_site_geojson_array"
                :key="component_map_key"
            />
        </div>
    </div>
</template>

<script>
    import Vue from 'vue'
    import datatable from '@vue-utils/datatable.vue'
    import uuid from 'uuid'
    import { api_endpoints, helpers, } from '@/utils/hooks'
    import ComponentMap from '@/components/common/apiary/component_map.vue'

    export default {
        props:{
            approval_id: {
                type: Number,
                required: true,
                default: 0,
            },
            is_external:{
              type: Boolean,
              default: false
            },
            is_internal:{
              type: Boolean,
              default: false
            },
        },
        data:function () {
            let vm=this;
            return{
                proposal_apiary: null,
                modalBindId: null,
                apiary_sites: [],
                component_map_key: '',
                apiary_site_geojson_array: [],
                dtHeaders: [
                    'Id',
                    'Site',
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
                                return '(site name)'
                            }
                        },
                        {
                            mRender: function (data, type, apiary_site) {
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
        components: {
            datatable,
            ComponentMap,
        },
        computed:{
            addButtonEnabled: function() {
                let enabled = false;
                try {
                    if(this.proposal_apiary.apiary_sites.length > 0){
                        enabled = true
                    }
                } catch(err) { }
                return enabled;
            }
        },
        watch:{

        },
        methods:{
            _get_basic_data: function(){
                let data = {
                    'category': '',
                    'profile': '', // TODO how to determine this?
                    'district': '',
                    //'application': '3',  // TODO Retrieve the id of the 'Temporary Use' type or handle it at the server side 
                                         //      like if there is apiary_temporary_use attribute, it must be a temporary use application, or so.
                    'sub_activity2': '',
                    'region': '',
                    'approval_level': '',
                    'behalf_of': '',  // TODO how to determine this?
                    'activity': '',
                    'sub_activity1': '',
                    'application_type_str': 'site_transfer',
                    //'approval_id': this.approval_id,
                }
                return data
            },

            createProposal:function () {
                console.log('createProposal');

                let vm = this;
                vm.creatingProposal = true;
                let data = vm._get_basic_data();

                vm.$http.post('/api/proposal.json', data).then(res => {
                    vm.proposal = res.body;

                    console.log('returned: ')
                    console.log(vm.proposal)

                    vm.$router.push({ name:"draft_proposal", params:{ proposal_id: vm.proposal.id }});
                    vm.creatingProposal = false;
                },
                err => {
                    console.log(err);
                });
            },

            openNewSiteTransfer: function() {
                let vm = this

                swal({
                    title: "Create Site Transfer Application",
                    text: "Are you sure you want to create a new site transfer application?",
                    type: "question",
                    showCancelButton: true,
                    confirmButtonText: 'Create'
                }).then(
                    () => {
                        vm.createProposal();
                    },
                    (error) => {

                    }
                );
            },

            loadApiarySites: async function(){
                console.log('loadApiarySites');

                await this.$http.get('/api/approvals/' + this.approval_id + '/apiary_site/').then(
                    (accept)=>{
                        console.log(accept.body)
                        this.apiary_sites = accept.body
                        this.constructSitesTable()
                    },
                    (reject)=>{
                    },
                )
                this.addApiarySitesToMap(this.apiary_sites)
            },
            addApiarySitesToMap: function(apiary_sites) {
                for (let i=0; i<apiary_sites.length; i++){
                    this.apiary_site_geojson_array.push(apiary_sites[i].as_geojson)
                }

                // Reload ComponentMap by assigning a new key value
                this.component_map_key = uuid()
            },
            constructSitesTable: function(){
                console.log('constructSitesTable');
                // Clear table
                this.$refs.site_availability_table.vmDataTable.clear().draw();

                // Construct table
                if (this.apiary_sites.length > 0){
                    for(let i=0; i<this.apiary_sites.length; i++){
                        this.addApiarySiteToTable(this.apiary_sites[i]);
                    }
                }
            },
            addApiarySiteToTable: function(apiary_site) {
                this.$refs.site_availability_table.vmDataTable.row.add(apiary_site).draw();
            },
            addEventListeners: function() {
                $("#site-availability-table").on("click", ".toggle_availability", this.toggleAvailability);
                $("#site-availability-table").on("click", ".view_on_map", this.zoomOnApiarySite);
            },
            updateApiarySite: function(site_updated) {
                // Update internal apiary_site data
                for (let i=0; i<this.apiary_sites.length; i++){
                    if (this.apiary_sites[i].id == site_updated.id){
                        this.apiary_sites[i].available = site_updated.available
                    }
                }
            },
            zoomOnApiarySite: function(e) {
                let apiary_site_id = e.target.getAttribute("data-apiary-site-id");
                this.$refs.component_map.zoomToApiarySiteById(apiary_site_id)
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
                        vm.constructSitesTable();
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
        },
        created: function() {
            console.log('in created')
            console.log('approval_id: ' + this.approval_id)
            this.loadApiarySites()
        },
        mounted: function() {
            let vm = this;
            this.$nextTick(() => {
                vm.addEventListeners();
                this.constructSitesTable();
            });
        }
    }
</script>

<style lang="css" scoped>

</style>
