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
            <FormSection :formCollapse="false" label="Site Locations" Index="site_locations">
                <div v-if="draftApiaryApplication">
                    <SiteLocations
                        :proposal="proposal"
                        id="site_locations"
                        ref="apiary_site_locations"
                        :is_external="is_external"
                        :is_internal="is_internal"
                        @button_text="button_text"
                    />
                </div>
                <div v-else>
                    <ComponentSiteSelection
                        :apiary_sites="apiary_sites"
                        :is_internal="is_internal"
                        :is_external="is_external"
                        :key="component_site_selection_key"
                      />
                </div>
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

    import SiteLocations from '@/components/common/apiary/site_locations.vue'
    import ComponentSiteSelection from '@/components/common/apiary/component_site_selection.vue'
    import FileField from '@/components/forms/filefield_immediate.vue'
    import FormSection from "@/components/forms/section_toggle.vue"
    import uuid from 'uuid'
    import {
        api_endpoints,
        helpers
    }from '@/utils/hooks'

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
                values:null,
                pBody: 'pBody'+vm._uid,
                checklist_answers : [],
                component_site_selection_key: '',
            }
        },
        components: {
            SiteLocations,
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
                if (this.proposal && this.proposal.proposal_apiary) {
                    return this.proposal.proposal_apiary.apiary_sites;
                }
            },
            draftApiaryApplication: function() {
                let draftStatus = false;
                if (this.is_external && this.proposal && this.proposal.application_type === 'Apiary' && this.proposal.customer_status === 'Draft') {
                    draftStatus = true;
                }
                return draftStatus;
            },

          //applicantType: function(){
          //  return this.proposal.applicant_type;
          //},
        },
        methods:{
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

        },
        mounted: function() {
            //let vm = this;
            this.component_site_selection_key = uuid()
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

</style>

