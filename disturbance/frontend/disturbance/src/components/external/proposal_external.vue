<template lang="html">
    <div class="container" >
        <form :action="proposal_form_url" method="post" name="new_proposal" enctype="multipart/form-data">
            <div v-if="!proposal_readonly">
              <div v-if="hasAmendmentRequest" class="row" style="color:red;">
                <div class="col-lg-12 pull-right">
                    <div class="panel panel-default">
                      <div class="panel-heading">
                        <h3 class="panel-title" style="color:red;">An amendment has been requested for this Proposal
                          <a class="panelClicker" :href="'#'+pBody" data-toggle="collapse"  data-parent="#userInfo" expanded="true" :aria-controls="pBody">
                                <span class="glyphicon glyphicon-chevron-down pull-right "></span>
                          </a>
                        </h3>
                      </div>
                      <div class="panel-body collapse in" :id="pBody">
                        <div v-for="a in amendment_request">
                          <p>Reason: {{a.reason}}</p>
                          <p v-if="a.amendment_request_documents">Documents:<p v-for="d in a.amendment_request_documents"><a :href="d._file" target="_blank" class="control-label pull-left">{{d.name   }}</a><br></p></p>
                          <p>Details: <p v-for="t in splitText(a.text)">{{t}}</p></p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!--
            <label for="region-label">Region(*)</label>
            <input type="text" name="region-text"class="form-control" disabled="true">
            -->

            <div id="error" v-if="missing_fields.length > 0" style="margin: 10px; padding: 5px; color: red; border:1px solid red;">
                <b>Please answer the following mandatory question(s):</b>
                <ul>
                    <li v-for="error in missing_fields">
                        {{ error.label }}
                    </li>
                </ul>
            </div>

            <div v-if="proposal && proposal.application_type=='Apiary'">

                <ProposalApiary
                    v-if="proposal"
                    :proposal="proposal"
                    id="proposalStart"
                    :showSections="sectionShow"
                    ref="proposal_apiary"
                    :is_external="true"
                    @button_text="button_text"
                />
            </div>
            <div v-else-if="proposal && proposal.application_type=='Site Transfer'">
                <ApiarySiteTransfer
                    v-if="proposal"
                    :proposal="proposal"
                    id="proposalStart"
                    :showSections="sectionShow"
                    ref="proposal_apiary"
                    :is_external="true"
                    @button_text="button_text"
                />
            </div>

            <div v-else>
                <ProposalDisturbance v-if="proposal" :proposal="proposal" id="proposalStart" :showSections="sectionShow"></ProposalDisturbance>
                <NewApply v-if="proposal" :proposal="proposal"></NewApply>
            </div>

            <div>
                <input type="hidden" name="csrfmiddlewaretoken" :value="csrf_token"/>
                <input type='hidden' name="schema" :value="JSON.stringify(proposal)" />
                <input type='hidden' name="proposal_id" :value="1" />

                <div class="row" style="margin-bottom: 50px">
                  <div class="navbar navbar-fixed-bottom" style="background-color: #f5f5f5 ">
                  <div class="navbar-inner">
                    <div v-if="proposal && !proposal.readonly" class="container">
                      <p class="pull-right" style="margin-top:5px;">
                        <!--div v-if="proposal && !proposal.apiary_group_application_type"-->
                        <input
                        id="sectionHide"
                        v-if="proposal && !proposal.apiary_group_application_type"
                        type="button"
                        @click.prevent="sectionHide"
                        class="btn btn-primary"
                        value="Show/Hide Sections"/>
                        <!--button id="sectionHide" @click.prevent="sectionHide" class="btn btn-primary">Show/Hide sections</button-->
                        <!--
                        <input type="button" @click.prevent="save_exit" class="btn btn-primary" value="Save and Exit"/>
                        <input type="button" @click.prevent="save" class="btn btn-primary" value="Save and Continue"/>

                        <input v-if="!isSubmitting" type="button" @click.prevent="submit" class="btn btn-primary" value="Submit"/>
                        <button v-else disabled class="btn btn-primary"><i class="fa fa-spin fa-spinner"></i>&nbsp;Submitting</button>

                        <input id="save_and_continue_btn" type="hidden" @click.prevent="save_wo_confirm" class="btn btn-primary" value="Save Without Confirmation"/>
                        -->
                        <input type="button" @click.prevent="save_exit" class="btn btn-primary" value="Save and Exit"/>
                        <input type="button" @click.prevent="save(true)" class="btn btn-primary" value="Save and Continue"/>

                        <input v-if="!isSubmitting" type="button" @click.prevent="submit" class="btn btn-primary" :value="submit_button_text"/>
                        <button v-else disabled class="btn btn-primary"><i class="fa fa-spin fa-spinner"></i>&nbsp;Submitting</button>

                        <input id="save_and_continue_btn" type="hidden" @click.prevent="save(false)" class="btn btn-primary" value="Save Without Confirmation"/>
                      </p>
                    </div>
                    <div v-else class="container">
                      <p class="pull-right" style="margin-top:5px;">
                        <!--button id="sectionHide" @click.prevent="sectionHide" class="btn btn-primary">Show/Hide sections</button-->
                        <input
                        id="sectionHide"
                        v-if="proposal && !proposal.apiary_group_application_type"
                        type="button"
                        @click.prevent="sectionHide"
                        class="btn btn-primary"
                        value="Show/Hide Sections"/>

                        <router-link class="btn btn-primary" :to="{name: 'external-proposals-dash'}">Back to Dashboard</router-link>
                      </p>
                    </div>
                  </div>
                  </div>
                </div>
            </div>

        </form>
    </div>
</template>
<script>
import ProposalDisturbance from '../form.vue'
import ProposalApiary from '../form_apiary.vue'
import ApiarySiteTransfer from '../form_apiary_site_transfer.vue'
import NewApply from './proposal_apply_new.vue'
import Vue from 'vue'
import {
  api_endpoints,
  helpers
}
from '@/utils/hooks'
export default {
    data: function() {
        return {
            "proposal": null,
            "loading": [],
            form: null,
            amendment_request: [],
            //isDataSaved: false,
            proposal_readonly: true,
            hasAmendmentRequest: false,
            submitting: false,
            submittingProposal: false,
            newText: "",
            pBody: 'pBody',
            missing_fields: [],
            sectionShow: true,
            submit_button_text: 'Pay and submit',
        }
    },
    components: {
        ProposalDisturbance,
        ProposalApiary,
        NewApply,
        ApiarySiteTransfer,
    },
    computed: {
        isLoading: function() {
          return this.loading.length > 0
        },
        isSubmitting: function() {
          return this.submittingProposal;
        },
        csrf_token: function() {
          return helpers.getCookie('csrftoken')
        },
        application_fee_url: function() {
          return (this.proposal) ? `/application_fee/${this.proposal.id}/` : '';
        },
        proposal_form_url: function() {
          return (this.proposal) ? `/api/proposal/${this.proposal.id}/draft.json` : '';
        },
        proposal_submit_url: function() {
          return (this.proposal) ? `/api/proposal/${this.proposal.id}/submit.json` : '';
          //return this.submit();
        },
        //submit_button_text: function() {
        //    if (!this.proposal.fee_paid && this.proposal.application_type=='Apiary') {
        //        return 'Pay and submit'
        //    } else {
        //        return 'Submit'
        //    }
        //}
    },
    methods: {
        button_text: function(button_text){
            console.log('button text updated: ' + button_text)
            this.submit_button_text = button_text
        },
        //updateApiarySitesData: function() {
        //    if (this.proposal && this.proposal.proposal_apiary){
        //        this.$refs.proposal_apiary.$refs.apiary_site_locations.updateApiarySitesData()
        //    }
        //},
        //getFeatures: function() {
        //    let ret_obj = null
        //    if (this.proposal && this.proposal.proposal_apiary){
        //        ret_obj = this.$refs.proposal_apiary.$refs.apiary_site_locations.getFeatures()
        //    }
        //    return ret_obj
        //},
        attach_apiary_sites_data: function(formData){
            try {
                // Append apiary_sites edited data
                if (this.proposal && this.proposal.proposal_apiary){
                    let allFeatures = this.$refs.proposal_apiary.$refs.apiary_site_locations.getFeatures()
                    formData.append('all_the_features', JSON.stringify(allFeatures))
                }
                return formData
            } catch (err) {
                return formData
            }
        },
        save: function(confirmation_required) {
            console.log('in save');

            let vm = this;
            vm.form=document.forms.new_proposal;

            let formData = new FormData(vm.form);
            // Add apiary_sites data if needed
            formData = this.attach_apiary_sites_data(formData)

            console.log('formData: ')
            console.log(formData)
            console.log('url: ' + vm.proposal_form_url)

            vm.$http.post(vm.proposal_form_url, formData).then(
                res=>{
                    if (confirmation_required){
                        swal(
                            'Saved',
                            'Your proposal has been saved',
                            'success'
                        );
                    }
                },
                err=>{

                }
            );
        },
        save_exit: function(e) {
            let vm = this;
            vm.form=document.forms.new_proposal;
            this.submitting = true;
            this.save(true);

            // redirect back to dashboard
            vm.$router.push({
                name: 'external-proposals-dash'
            });
        },
        sectionHide: function(e) {
            let vm = this;
            vm.sectionShow=!vm.sectionShow
            //console.log(vm.sectionShow);
        },
        setdata: function(readonly){
            this.proposal_readonly = readonly;
        },
        setAmendmentData: function(amendment_request){
            this.amendment_request = amendment_request;
            if (amendment_request.length > 0)
                this.hasAmendmentRequest = true;
        },
        splitText: function(aText){
            let newText = '';
            newText = aText.split("\n");
            return newText;
        },
        leaving: function(e) {
            let vm = this;
            var dialogText = 'You have some unsaved changes.';
            if (!vm.proposal_readonly && !vm.submitting){
                e.returnValue = dialogText;
                return dialogText;
            }
            else{
                return null;
            }
        },
        highlight_missing_fields: function(){
            let vm = this;
            for (var missing_field of vm.missing_fields) {
                $("#" + missing_field.id).css("color", 'red');
            }
        },
        validate: function(){
            let vm = this;

            // reset default colour
            for (var field of vm.missing_fields) {
                $("#" + field.id).css("color", '#515151');
            }
            vm.missing_fields = [];

            // get all required fields, that are not hidden in the DOM
            //var hidden_fields = $('input[type=text]:hidden, textarea:hidden, input[type=checkbox]:hidden, input[type=radio]:hidden, input[type=file]:hidden');
            //hidden_fields.prop('required', null);
            //var required_fields = $('select:required').not(':hidden');
            var required_fields = $('input[type=text]:required, textarea:required, input[type=checkbox]:required, input[type=radio]:required, input[type=file]:required, select:required').not(':hidden');

            // loop through all (non-hidden) required fields, and check data has been entered
            required_fields.each(function() {
                //console.log('type: ' + this.type + ' ' + this.name)
                var id = 'id_' + this.name
                if (this.type == 'radio') {
                    //if (this.type == 'radio' && !$("input[name="+this.name+"]").is(':checked')) {
                    if (!$("input[name="+this.name+"]").is(':checked')) {
                        var text = $('#'+id).text()
                        console.log('radio not checked: ' + this.type + ' ' + text)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'checkbox') {
                    var id = 'id_' + this.className
                    if ($("[class="+this.className+"]:checked").length == 0) {
                        try { var text = $('#'+id).text() } catch(error) { var text = $('#'+id).textContent }
                        console.log('checkbox not checked: ' + this.type + ' ' + text)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'select-one') {
                    if ($(this).val() == '') {
                        var text = $('#'+id).text()  // this is the (question) label
                        var id = 'id_' + $(this).prop('name'); // the label id
                        console.log('selector not selected: ' + this.type + ' ' + text)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'file') {
                    var num_files = $('#'+id).attr('num_files')
                    if (num_files == "0") {
                        var text = $('#'+id).text()
                        console.log('file not uploaded: ' + this.type + ' ' + this.name)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'text') {
                    if (this.value == '') {
                        var text = $('#'+id).text()
                        console.log('text not provided: ' + this.type + ' ' + this.name)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'textarea') {
                    if (this.value == '') {
                        var text = $('#'+id).text()
                        console.log('textarea not provided: ' + this.type + ' ' + this.name)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                /*
                if (this.type == 'select') {
                    if (this.value == '') {
                        var text = $('#'+id).text()
                        console.log('select not provided: ' + this.type + ' ' + this.name)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }

                if (this.type == 'multi-select') {
                    if (this.value == '') {
                        var text = $('#'+id).text()
                        console.log('multi-select not provided: ' + this.type + ' ' + this.name)
                        vm.missing_fields.push({id: id, label: text});
                    }
                }
                */
            });

            return vm.missing_fields.length

            /*
            if (emptyFields === 0) {
                $('#form').submit();
            } else {
                $('#error').show();
                return false;
            }
            */
        },

        can_submit: function() {
            let vm=this;
            let blank_fields = []

            //console.log('can_submit checklistq check' +vm.$refs.proposal_apiary.getUnansweredChecklistQuestions());

             if(vm.proposal.application_type == 'Apiary'){
                if( vm.$refs.proposal_apiary.getUnansweredChecklistQuestions ){
                    blank_fields.push(' You have unanswered checklist questions');
                }

                if(vm.$refs.proposal_apiary.$refs.deed_poll_documents.documents.length==0){
                    blank_fields.push(' Deed poll document is missing')
                }
             }

            if(blank_fields.length==0){
                return true;
            }
            else {
                return blank_fields;
            }
        },

        highlight_deficient_fields: function(deficient_fields){
            let vm = this;
            for (var deficient_field of deficient_fields) {
                $("#" + "id_"+deficient_field).css("color", 'red');
            }
        },

        deficientFields(){
            let vm=this;
            //console.log("I am here");
            let deficient_fields=[]
            $('.deficiency').each((i,d) => {
                if($(d).val() != ''){
                    var name=$(d)[0].name
                    var tmp=name.replace("-comment-field","")
                    deficient_fields.push(tmp);
                    //console.log('data', $("#"+"id_" + tmp))
                }
            });
            //console.log('deficient fields', deficient_fields);
            vm.highlight_deficient_fields(deficient_fields);
        },
        submit: function(){
            console.log('submit');

            let vm = this;
            vm.form=document.forms.new_proposal;
            let formData = new FormData(vm.form);
            // Add apiary_sites data if needed
            formData = this.attach_apiary_sites_data(formData)

            let missing_data = vm.can_submit();
            if(missing_data!=true){
              swal({
                title: "Please fix following errors before submitting",
                text: missing_data,
                type:'error'
              })
            //vm.paySubmitting=false;
            return false;
            }

            var num_missing_fields = vm.validate()
            if (num_missing_fields > 0) {
                vm.highlight_missing_fields()
                var top = ($('#error').offset() || { "top": NaN }).top;
                $('html, body').animate({
                    scrollTop: top
                }, 1);
                return false;
            }

            // remove the confirm prompt when navigating away from window (on button 'Submit' click)
            vm.submitting = true;

            swal({
                title: "Submit Proposal",
                text: "Are you sure you want to submit this proposal?",
                type: "question",
                showCancelButton: true,
                confirmButtonText: 'Submit'
            }).then(() => {
                console.log('in then()');
                vm.submittingProposal = true;
                // Only Apiary has an application fee
                if (!vm.proposal.fee_paid && vm.proposal.application_type=='Apiary') {
                    vm.save_and_redirect();
                } else {
                    /* just save and submit - no payment required (probably application was pushed back by assessor for amendment */
                    //vm.save_wo_confirm()
                    vm.save(false)
                    vm.$http.post(helpers.add_endpoint_json(api_endpoints.proposals,vm.proposal.id+'/submit'),formData).then(res=>{
                        vm.proposal = res.body;
                        vm.$router.push({
                            name: 'submit_proposal',
                            params: { proposal: vm.proposal}
                        });
                    },err=>{
                        swal(
                            'Submit Error',
                            helpers.apiVueResourceError(err),
                            'error'
                        )
                    });
                }
            },(error) => {
              vm.paySubmitting=false;
            });
            //vm.submittingProposal= false;
        },
        // Apiary submission
        save_and_redirect: async function(e) {
            console.log('save_and_redirect');
            let vm = this;
            vm.form=document.forms.new_proposal;
            let formData = new FormData(vm.form);
            // Add apiary_sites data if needed
            formData = this.attach_apiary_sites_data(formData)

            vm.$http.post(vm.proposal_submit_url,formData).then(res=>{
                /* after the above save, redirect to the Django post() method in ApplicationFeeView */
                vm.post_and_redirect(vm.application_fee_url, {'csrfmiddlewaretoken' : vm.csrf_token});
            },err=>{
            });
        },
        post_and_redirect: function(url, postData) {
            /* http.post and ajax do not allow redirect from Django View (post method),
               this function allows redirect by mimicking a form submit.

               usage:  vm.post_and_redirect(vm.application_fee_url, {'csrfmiddlewaretoken' : vm.csrf_token});
            */
            var postFormStr = "<form method='POST' action='" + url + "'>";

            for (var key in postData) {
                if (postData.hasOwnProperty(key)) {
                    postFormStr += "<input type='hidden' name='" + key + "' value='" + postData[key] + "'>";
                }
            }
            postFormStr += "</form>";
            var formElement = $(postFormStr);
            $('body').append(formElement);
            $(formElement).submit();
        },
    },
    mounted: function() {
        console.log('in mounted')

        let vm = this;
        vm.form = document.forms.new_proposal;
        window.addEventListener('beforeunload', vm.leaving);
        window.addEventListener('onblur', vm.leaving);
        // this.$nextTick(() => {
        //   console.log("I am here1");
        //         if(vm.hasAmendmentRequest){
        //           console.log("I am here2");
        //             vm.deficientFields();
        //         }
        //     });
    },
    updated: function(){
        console.log('in updated')

        let vm=this;
        this.$nextTick(() => {
            if(vm.hasAmendmentRequest){
                vm.deficientFields();
            }
        });
    },
    created: function() {
        console.log('in created')
        console.log('proposal_id: ' + this.$route.params.proposal_id)
        let proposal_id = this.$route.params.proposal_id

        let vm = this;
        Vue.http.get(`/api/proposal/${ proposal_id }.json`).then(
            res => {
                vm.loading.push('fetching proposal')
                vm.proposal = res.body;
                console.log('vm.proposal')
                console.log(vm.proposal)
                vm.loading.splice('fetching proposal', 1);
                vm.setdata(vm.proposal.readonly);

                Vue.http.get(helpers.add_endpoint_json(api_endpoints.proposals, proposal_id + '/amendment_request')).then((res) => {
                    vm.setAmendmentData(res.body);
                },
                err => {
                    console.log(err);
                });
            },
            err => {
                console.log(err);
            }
        );
    },
    beforeRouteEnter: function(to, from, next) {
        console.log('in beforeRouteEnter')
        console.log('id: ' + to.params.proposal_id)
    }
}
</script>

<style lang="css">
</style>
