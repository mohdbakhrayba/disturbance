<template lang="html">
    <div>
        <div v-if="is_external" class="col-md-3">
            <div>
                <h3>Application: {{ proposal.lodgement_number }}</h3>
                <h4>Application Type: {{proposal.proposal_type }}</h4>
                <h4>Status: {{proposal.customer_status }}</h4>
            </div>
        </div>

        <div :class="apiary_sections_classname">
            <!--FormSection :formCollapse="false" label="Site Locations" Index="site_locations">
                <SiteLocations
                    :proposal="proposal"
                    id="site_locations"
                    ref="apiary_site_locations"
                    :is_external="is_external"
                    :is_internal="is_internal"
                    @button_text="button_text"
                />
            </FormSection-->
            <FormSection :formCollapse="false" label="Transferee" Index="transferee">
                <!--span class="row col-sm-12"-->
                <div class="row col-sm-12">
                    <div class="form-group">
                        <!--div class="row form-control">
                            <label class="inline">Title:</label>
                        </div-->
                        <div class="col-sm-8">
                            <label class="emailLabel">Email:</label>
                            <input
                                type="text"
                                class="form-control"
                                v-model="transfereeEmail"
                                :readonly="readonly"
                            />
                        </div>
                        <input type="button" @click="lookupTransferee" value="Find existing licence" class="btn btn-primary">
                    </div>
                </div>
                <!--/span-->
                <div class="row col-sm-12">
                    <div class="form-group">
                        <div v-if="lookupErrorText">
                            Error: {{lookupErrorText}}
                        </div>
                        <div v-else-if="apiaryApprovals">
                            <div v-for="approval in apiaryApprovals">
                                <input type="radio" name="approval_choice" :value="approval.id" v-model="proposal.proposal_apiary.selected_licence"/>
                                Licence: {{approval.lodgement_number}}
                            </div>
                            <!--ul class="list-unstyled col-sm-12" v-for="approval in apiaryApprovals">
                                <div class="row">
                                    <div class="col-sm-12">
                                        <ul  class="list-inline col-sm-6">
                                            <li class="list-inline-item">
                                                <input  
                                                class="form-check-input" 
                                                v-model="selectedLicence" 
                                                ref="licenceSelection" 
                                                type="radio" 
                                                :name="approvalid" 
                                                :id="approvalid"
                                                :value="approval.id" 
                                                data-parsley-required 
                                                :disabled="readonly"/> Licence: {{approval.id}}
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </ul-->
                        </div>
                    </div>
                </div>

            </FormSection>
            <FormSection :formCollapse="false" label="Site" Index="site_locations">
                <ComponentSiteSelection
                    :apiary_sites="apiary_sites"
                    :is_internal="is_internal"
                    :is_external="is_external"
                    :key="component_site_selection_key"
                    ref="component_site_selection"
                    @apiary_sites_updated="apiarySitesUpdated"
                  />
            </FormSection>

            <FormSection :formCollapse="false" label="Deed Poll" Index="deed_poll">
                <div class="row">
                    <div class="col-sm-12">
                        <label>Print <a :href="deedPollUrl" target="_blank">the deed poll</a>, sign it, have it witnessed and attach it to this application.</label>
                    </div>
                </div>
                <div class="row">
                    <div class="col-sm-12">
                        <FileField
                            ref="deed_poll_documents"
                            name="deed-poll-documents"
                            :isRepeatable="false"
                            :documentActionUrl="deedPollDocumentUrl"
                            :readonly="readonly"
                        />
                    </div>
                </div>
            </FormSection>

            <FormSection :formCollapse="false" label="Checklist" Index="checklist">
                <ul class="list-unstyled col-sm-12" v-for="q in proposal.proposal_apiary.checklist_answers">
                    <div class="row">
                        <div class="col-sm-12">
                            <li class="col-sm-6">
                                <label class="control-label">{{q.question.text}}</label>
                            </li>

                            <ul  class="list-inline col-sm-6">
                                <li class="list-inline-item">
                                    <input  class="form-check-input" v-model="q.answer" ref="Checkbox" type="radio" :name="'option'+q.id" :id="'answer_one'+q.id":value="true" data-parsley-required :disabled="readonly"/> Yes
                                </li>
                                <li class="list-inline-item">
                                    <input  class="form-check-input" v-model="q.answer" ref="Checkbox" type="radio" :name="'option'+q.id" :id="'answer_two'+q.id" :value="false" data-parsley-required :disabled="readonly"/> No
                                </li>
                            </ul>
                        </div>
                    </div>
                </ul>
            </FormSection>
        </div>

    </div>
</template>

<script>

    //import SiteLocations from '@/components/common/apiary/site_locations.vue'
    import FileField from '@/components/forms/filefield_immediate.vue'
    import FormSection from "@/components/forms/section_toggle.vue"
    import Vue from 'vue'
    import ComponentSiteSelection from '@/components/common/apiary/component_site_selection.vue'
    import uuid from 'uuid'
    import {
        api_endpoints,
        helpers
    }from '@/utils/hooks'

    export default {
        name: 'ApiarySiteTransferForm',
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
                values:null,
                pBody: 'pBody'+vm._uid,
                checklist_answers : [],
                transfereeEmail: '',
                //apiaryApprovals: {},
                apiaryApprovals: null,
                lookupErrorText: '',
                //selectedLicence: null,
                component_site_selection_key: '',
                apiary_sites_local: [],
            }
        },
        components: {
            //SiteLocations,
            ComponentSiteSelection,
            FileField,
            FormSection,
        },
        computed:{
            apiary_sections_classname: function() {
                // For external page, we need 'col-md-9' classname
                // but not for the internal.
                // This is a hacky way, though...
                if(this.is_internal){
                    return ''
                } else {
                    return 'col-md-9'
                }
            },
            deedPollDocumentUrl: function() {
                let url = '';
                if (this.proposal && this.proposal.proposal_apiary) {
                    url = helpers.add_endpoint_join(
                        //api_endpoints.proposal_apiary,
                        '/api/proposal_apiary/',
                        this.proposal.proposal_apiary.id + '/process_deed_poll_document/'
                        )
                }
                return url;
            },
            deedPollUrl: function() {
                return '';
            },
            readonly: function() {
                let readonlyStatus = true;
                if (this.proposal.customer_status === 'Draft' && !this.is_internal) {
                    readonlyStatus = false;
                }
                return readonlyStatus;
            },
            getUnansweredChecklistQuestions: function() {
                let UnansweredChecklistQuestions = false;

                if(this.proposal && this.proposal.proposal_apiary.checklist_answers){
                    let numOfAnswers = this.proposal.proposal_apiary.checklist_answers.length;
                    for( let i=0; i< numOfAnswers ; i ++){
                        //console.log('ans [ '+i+'] '+this.proposal.proposal_apiary.checklist_answers[i].answer)
                        if(this.proposal.proposal_apiary.checklist_answers[i].answer == null){
                            UnansweredChecklistQuestions = true;
                        }
                    }
                }

                return UnansweredChecklistQuestions;

            },
            apiary_sites: function() {
                let sites = []
                if (this.proposal && this.proposal.proposal_apiary) {
                    for (let site of this.proposal.proposal_apiary.site_transfer_apiary_sites) {
                        sites.push(site.apiary_site);
                    }
                }
                return sites;
            },
            /*
            site_transfer_apiary_sites: function(){
                let sites = []
                if (this.proposal && this.proposal.proposal_apiary) {
                    for (let site of this.proposal.proposal_apiary.site_transfer_apiary_sites) {
                        sites.push({'id': site.id, 'checked': site.apiary_site.checked})
                    }
                }
                return sites;
            },
            */
          //applicantType: function(){
          //  return this.proposal.applicant_type;
          //},
        },
        methods:{
            apiarySitesUpdated: function(apiarySitesLocal) {
                this.apiary_sites_local = apiarySitesLocal;
            },
            button_text: function(button_text) {
                this.$emit('button_text', button_text)
            },
            getChecklistAnswers: function() {
                let vm = this;
                this.checklist_answers.push({
                    'id' : 'this.proposal.proposal_apiary.checklist_answers.id',
                    'answer' : 'this.proposal.proposal_apiary.checklist_answers.answer'
                 })
             return checklist_answers;
            },
            lookupTransferee: function() {
                this.lookupErrorText = '';
                console.log(this.transfereeEmail);
                //let url = `/api/proposal_apiary/${this.proposal.proposal_apiary.id}/get_apiary_approvals.json`
                Vue.http.post(helpers.add_endpoint_json(
                    api_endpoints.proposal_apiary,this.proposal.proposal_apiary.id+'/get_apiary_approvals'),
                    //data,{
                    {'user_email': this.transfereeEmail}).then(res => {
                        console.log(res.body);
                        if (res.body && res.body.apiary_approvals) {
                            this.apiaryApprovals = res.body.apiary_approvals.approvals;
                            if (this.apiaryApprovals.length < 1) {
                                this.lookupErrorText = 'No current licence for the transferee';
                            }
                        } else {
                            this.lookupErrorText = res.body;
                        }
                },
                err => {
                  console.log(err);
                });

            },

        },
        mounted: function() {
            //let vm = this;
            this.component_site_selection_key = uuid()
            // set initial checked status
            if (this.proposal && this.proposal.proposal_apiary) {
                for (let site of this.proposal.proposal_apiary.site_transfer_apiary_sites) {
                    site.apiary_site.checked = site.selected;
                }
            }

            //vm.form = document.forms.new_proposal;
            //window.addEventListener('beforeunload', vm.leaving);
            //window.addEventListener('onblur', vm.leaving);
        }

    }
</script>

<style lang="css" scoped>
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
    .emailLabel{
        text-align: left;
    }
</style>

