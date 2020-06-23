<template lang="html">
    <div>

        <div class="row col-sm-12">
            <div class="col-sm-6">
                <datatable
                    ref="table_apiary_site"
                    id="table-apiary-site"
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

    </div>
</template>

<script>
    import datatable from '@vue-utils/datatable.vue'
    import ComponentMap from '@/components/common/apiary/component_map.vue'

    export default {
        props:{
            apiary_sites_with_selection: {
                type: Array,
                default: function(){
                    return [];
                }
            },
        },
        watch: {

        },
        data: function(){
            return{
                component_map_key: '',
                apiary_site_geojson_array: [],
                dtHeaders: [
                    'Id',
                    '',
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
                            visible: false,
                            mRender: function (data, type, full) {
                                console.log(full);
                                return full.apiary_site.id;
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                if (full.selected){
                                    return '<input type="checkbox" class="site_checkbox" data-apiary-site-id="' + full.apiary_site.id + '" checked/>'
                                } else {
                                    return '<input type="checkbox" class="site_checkbox" data-apiary-site-id="' + full.apiary_site.id + '" />'
                                }
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                return 'site:' + full.apiary_site.id
                            }
                        },
                        {
                            mRender: function (data, type, full) {
                                let ret = '<a><span class="view_on_map" data-apiary-site-id="' + full.apiary_site.id + '"/>View on Map (TODO)</span></a>';
                                return ret;
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
                this.constructApiarySitesTable();
            });
        },
        components: {
            ComponentMap,
            datatable,
        },
        computed: {

        },
        methods: {
            constructApiarySitesTable: function() {
                // Clear table
                this.$refs.table_apiary_site.vmDataTable.clear().draw();

                // Construct table
                if (this.apiary_sites_with_selection.length > 0){
                    for(let i=0; i<this.apiary_sites_with_selection.length; i++){
                        this.addApiarySiteToTable(this.apiary_sites_with_selection[i]);
                    }
                }
            },
            addApiarySiteToTable: function(apiary_site_with_selection) {
                this.$refs.table_apiary_site.vmDataTable.row.add(apiary_site_with_selection).draw();
            },
            addEventListeners: function () {

            },
            emitContentsChangedEvent: function () {
                this.$emit('contents_changed', {

                });
            },
        },
    }
</script>

<style lang="css" scoped>
.component-site-selection {
    border: solid 2px #5BB;
}
</style>
