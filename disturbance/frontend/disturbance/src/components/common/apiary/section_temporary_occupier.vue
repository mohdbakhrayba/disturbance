<template lang="html">
    <div>

        <div class="form-group"><div class="row">
            <label class="col-sm-2">Name</label>
            <div class="col-sm-4">
                <input type="text" class="form-control" v-model="occupier_name" :disabled="is_readonly"/>
            </div>
        </div></div>
        <div class="form-group"><div class="row">
            <label class="col-sm-2">Phone</label>
            <div class="col-sm-4">
                <input type="text" class="form-control" v-model="occupier_phone" :disabled="is_readonly"/>
            </div>
        </div></div>
        <div class="form-group"><div class="row">
            <label class="col-sm-2">Mobile</label>
            <div class="col-sm-4">
                <input type="text" class="form-control" v-model="occupier_mobile" :disabled="is_readonly"/>
            </div>
        </div></div>
        <div class="form-group"><div class="row">
            <label class="col-sm-2">Email</label>
            <div class="col-sm-4">
                <input type="text" class="form-control" v-model="occupier_email" :disabled="is_readonly"/>
            </div>
        </div></div>

    </div>
</template>

<script>
    export default {
        name: 'SectionTemporaryOccupier',
        props:{
            name: {
                type: String,
                default: '',
            },
            phone: {
                type: String,
                default: '',
            },
            mobile: {
                type: String,
                default: '',
            },
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
            occupier_name: function(){
                this.emitContentsChangedEvent();
            },
            occupier_phone: function(){
                this.emitContentsChangedEvent();
            },
            occupier_mobile: function(){
                this.emitContentsChangedEvent();
            },
            occupier_email: function(){
                this.emitContentsChangedEvent();
            },
        },
        data: function(){
            return{
                occupier_name: '',
                occupier_phone: '',
                occupier_mobile: '',
                occupier_email: '',
            }
        },
        created: function(){
            this.occupier_name = this.name;
            this.occupier_phone = this.phone;
            this.occupier_mobile = this.mobile;
            this.occupier_email = this.email;
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
                    'occupier_name': this.occupier_name,
                    'occupier_phone': this.occupier_phone,
                    'occupier_mobile': this.occupier_mobile,
                    'occupier_email': this.occupier_email,
                });
            },
        },
    }
</script>

<style lang="css" scoped>
</style>
