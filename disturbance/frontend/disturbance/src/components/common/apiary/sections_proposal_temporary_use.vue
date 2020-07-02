<template>
    <div>

        <FormSection :formCollapse="false" label="Period and Site(s)" Index="period_and_sites">
            <template v-if="proposal && proposal.apiary_temporary_use">
                <PeriodAndSites 
                    :is_external="is_external" 
                    :is_internal="is_internal" 
                    :is_readonly="is_readonly"
                    :from_date="proposal.apiary_temporary_use.from_date"
                    :to_date="proposal.apiary_temporary_use.to_date"
                    :temporary_use_apiary_sites="proposal.apiary_temporary_use.temporary_use_apiary_sites"
                    :existing_temporary_uses="existing_temporary_uses"
                    @from_date_changed="fromDateChanged"
                    @to_date_changed="toDateChanged"
                    @apiary_sites_updated="apiarySitesUpdated"
                    :key="period_and_sites_key"
                />
            </template>
        </FormSection>

        <FormSection :formCollapse="false" label="Temporary Occupier" Index="temporary_occupier">
            <template v-if="proposal && proposal.apiary_temporary_use">
                <TemporaryOccupier 
                    :is_external="is_external"
                    :is_internal="is_internal"
                    :name="proposal.apiary_temporary_use.temporary_occupier_name"
                    :phone="proposal.apiary_temporary_use.temporary_occupier_phone"
                    :mobile="proposal.apiary_temporary_use.temporary_occupier_mobile"
                    :email="proposal.apiary_temporary_use.temporary_occupier_email"
                    :is_readonly="is_readonly"
                    @contents_changed="occupierDataChanged"
                    :key="temporary_occupier_key"
                />
            </template>
        </FormSection>

        <FormSection :formCollapse="false" label="Deed Poll" Index="deed_poll">
            <template v-if="proposal && proposal.apiary_temporary_use && documentActionUrl">
                <DeedPoll
                    :isRepeatable="false"
                    :isReadonly="is_readonly"
                    :documentActionUrl="documentActionUrl"
                />
            </template>
        </FormSection>
<!--
        <div style="margin-bottom: 50px">
            <div class="navbar navbar-fixed-bottom" style="background-color: #f5f5f5 ">
                <div class="navbar-inner">
                    <div class="container">
                        <p class="pull-right" style="margin-top:5px;">
                            <input type="button" @click.prevent="save_exit" class="btn btn-primary" value="Save and Exit"/>
                            <input type="button" @click.prevent="save" class="btn btn-primary" value="Save and Continue"/>
                            <input v-if="!isSubmitting" type="button" @click.prevent="submit" class="btn btn-primary" value="Submit"/>
                            <button v-else disabled class="btn btn-primary"><i class="fa fa-spin fa-spinner"></i>&nbsp;Submitting</button>
                        </p>
                    </div>
                </div>
            </div>
        </div>
-->

    </div>
</template>

<script>
    import Vue from 'vue'
    import datatable from '@vue-utils/datatable.vue'
    import uuid from 'uuid'
    import { api_endpoints, helpers, } from '@/utils/hooks'
    import FormSection from "@/components/forms/section_toggle.vue"
    import PeriodAndSites from "@/components/common/apiary/section_period_and_sites.vue"
    import TemporaryOccupier from "@/components/common/apiary/section_temporary_occupier.vue"
    import DeedPoll from "@/components/common/apiary/section_deed_poll.vue"

    export default {
        name: 'SectionsProposalTemporaryUse',
        props:{
            is_external: {
                type: Boolean,
                default: false,
            },
            is_internal: {
                type: Boolean,
                default: false,
            },
            proposal: {
                type: Object,
                default: null,
            }
        },
        data:function () {
            let vm=this;

            return{
                period_and_sites_key: '',
                temporary_occupier_key: '',
                pBody: 'pBody'+vm._uid,
                licence: null,
                from_date_enabled: true,
                to_date_enabled: true,
                isSubmitting: false,
                application: {},
                apiary_sites_available: [],
                existing_temporary_uses: [],
            }
        },
        components: {
            DeedPoll,
            FormSection,
            datatable,
            PeriodAndSites,
            TemporaryOccupier,
        },
        computed:{
            csrf_token: function() {
              return helpers.getCookie('csrftoken')
            },
            documentActionUrl: function() {
                let url = '';
                if (this.proposal && this.proposal.apiary_temporary_use) {
                    url = helpers.add_endpoint_join(
                        '/api/proposal/',
                        this.proposal.id + '/process_deed_poll_document/'
                        )
                }
                return url;
            },
            is_readonly: function() {
                let readonlyStatus = true
                if (this.proposal && this.proposal.customer_status === 'Draft' && !this.is_internal) {
                    readonlyStatus = false
                }
                return readonlyStatus
            }
        },
        watch:{

        },
        methods:{
            occupierDataChanged: function(value){
                this.proposal.apiary_temporary_use.temporary_occupier_name = value.occupier_name
                this.proposal.apiary_temporary_use.temporary_occupier_phone = value.occupier_phone
                this.proposal.apiary_temporary_use.temporary_occupier_mobile = value.occupier_mobile
                this.proposal.apiary_temporary_use.temporary_occupier_email = value.occupier_email
            },
            fromDateChanged: function(value){
                this.proposal.apiary_temporary_use.from_date = moment(value, 'DD/MM/YYYY');
            },
            toDateChanged: function(value){
                this.proposal.apiary_temporary_use.to_date = moment(value, 'DD/MM/YYYY');
            },
            apiarySitesUpdated: function(apiary_sites){
                for (let i=0; i<apiary_sites.length; i++){
                    let temporary_use_apiary_site = this.proposal.apiary_temporary_use.temporary_use_apiary_sites.find(element => element.apiary_site.id == apiary_sites[i].id)
                    // Update temporary_use_apiary_site, which is sent to the backend when saving
                    temporary_use_apiary_site.apiary_site = apiary_sites[i]
                }
            },
            addEventListeners: function() {

            },
            processError: async function(err){
                console.log('in processError');
                let errorText = '';
                if (err.body.non_field_errors) {
                    // When non field errors raised
                    for (let i=0; i<err.body.non_field_errors.length; i++){
                        errorText += err.body.non_field_errors[i] + '<br />';
                    }
                } else if(Array.isArray(err.body)) {
                    // When general errors raised
                    for (let i=0; i<err.body.length; i++){
                        errorText += err.body[i] + '<br />';
                    }
                } else {
                    // When field errors raised
                    for (let field_name in err.body){
                        if (err.body.hasOwnProperty(field_name)){
                            errorText += field_name + ':<br />';
                            for (let j=0; j<err.body[field_name].length; j++){
                                errorText += err.body[field_name][j] + '<br />';
                            }
                        }
                    }
                }
                await swal("Error", errorText, "error");
            },
        },
        created: function() {

        },
        mounted: function() {
            let vm = this;
            this.$nextTick(() => {
                vm.addEventListeners();
            });
        }
    }
</script>

<style lang="css" scoped>

</style>
