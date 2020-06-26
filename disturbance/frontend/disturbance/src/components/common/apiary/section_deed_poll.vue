<template lang="html">
    <div>

        <div class="row">
            <div class="col-sm-12">
                <FileField
                    ref="deed_poll_documents"
                    name="deed-poll-documents"
                    :isRepeatable="isRepeatable"
                    :documentActionUrl="documentActionUrl"
                    :readonly="isReadonly"
                />
            </div>
        </div>

    </div>
</template>

<script>
    import FileField from '@/components/forms/filefield_immediate.vue'

    export default {
        name: 'SectionDeedPoll',
        props:{
            isRepeatable: {
                type: Boolean,
                default: true,
            },
            isReadonly: {
                type: Boolean,
                default: true,
            },
            documentActionUrl: {
                type: String,
                default: '',
            }
        },
        watch: {

        },
        data: function(){
            return{

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
            FileField,
        },
        computed: {
        },
        methods: {
            addEventListeners: function () {

            },
        },
    }
</script>

<style lang="css" scoped>

</style>
