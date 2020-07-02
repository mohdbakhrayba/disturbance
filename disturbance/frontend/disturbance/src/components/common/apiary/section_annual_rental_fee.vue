<template lang="html">
    <div>

        <div class="form-group row">
            <label class="col-sm-5">Do not charge annual rental fee until</label>
            <div class="col-sm-6">
                <div class="input-group date" ref="periodFromDatePicker">
                    <input type="text" class="form-control" placeholder="DD/MM/YYYY" id="no_charge_until" :readonly="is_readonly"/>
                    <span class="input-group-addon">
                        <span class="glyphicon glyphicon-calendar"></span>
                    </span>
                </div>
            </div>
        </div>

        <div class="form-group row">
            <label class="col-sm-5">Calendar year</label>
            <div class="col-sm-6">
                <select class="form-control">
                    <option>AHO</option>
                </select>
            </div>
        </div>

        <div class="form-group row">
            <label class="col-sm-5">Invoice</label>
            <div class="col-sm-6">
                invoices here
            </div>
        </div>

    </div>
</template>

<script>
    export default {
        name: 'SectionAnnualRentalFee',
        props:{
            email: {
                type: String,
                default: '',
            },
            is_readonly: {
                type: Boolean,
                default: true,
            },
        },
        watch: {
            occupier_email: function(){
                this.emitContentsChangedEvent();
            },
        },
        data: function(){
            return {
                occupier_email: this.email,  // Copy props to the local variable
            }
        },
        created: function(){

        },
        mounted: function(){
            let vm = this;
            this.$nextTick(() => {
                vm.addEventListeners();
            });
        },
        components: {

        },
        computed: {

        },
        methods: {
            addEventListeners: function () {

            },
            emitContentsChangedEvent: function () {
                this.$emit('contents_changed', {
                    'occupier_email': this.occupier_email,
                });
            },
        },
    }
</script>

<style lang="css" scoped>
</style>
