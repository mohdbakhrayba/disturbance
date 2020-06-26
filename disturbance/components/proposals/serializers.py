from disturbance.components.proposals.models import (
                                    ProposalType,
                                    Proposal,
                                    ProposalUserAction,
                                    ProposalLogEntry,
                                    Referral,
                                    ProposalRequirement,
                                    ProposalStandardRequirement,
                                    AmendmentRequest,
                                    AmendmentRequestDocument,
                                )
from disturbance.components.organisations.models import (
                                Organisation
                            )
from disturbance.components.main.serializers import CommunicationLogEntrySerializer
from rest_framework import serializers

from disturbance.components.proposals.serializers_apiary import ProposalApiarySerializer, \
    ProposalApiaryTemporaryUseSerializer
from disturbance.components.proposals.serializers_base import BaseProposalSerializer, ProposalReferralSerializer, \
    ProposalDeclinedDetailsSerializer, EmailUserSerializer


class ProposalTypeSerializer(serializers.ModelSerializer):
    activities = serializers.SerializerMethodField()
    class Meta:
        model = ProposalType
        fields = (
            'id',
            'schema',
            'activities'
        )


    def get_activities(self,obj):
        return obj.activities.names()


class ProposalWrapperSerializer(serializers.ModelSerializer):
    application_type_name = serializers.SerializerMethodField()
    class Meta:
        model = Proposal
        fields = (
            'id',
            'application_type_name',
        )

    def get_application_type_name(self,obj):
        return obj.application_type.name


class DTProposalSerializer(BaseProposalSerializer):
    submitter = EmailUserSerializer()
    applicant = serializers.CharField(source='applicant.organisation.name')
    processing_status = serializers.SerializerMethodField(read_only=True)
    review_status = serializers.SerializerMethodField(read_only=True)
    customer_status = serializers.SerializerMethodField(read_only=True)
    assigned_officer = serializers.CharField(source='assigned_officer.get_full_name', allow_null=True)

    application_type = serializers.CharField(source='application_type.name', read_only=True)
    region = serializers.CharField(source='region.name', read_only=True)
    district = serializers.CharField(source='district.name', read_only=True)
    #tenure = serializers.CharField(source='tenure.name', read_only=True)


class ListProposalSerializer(BaseProposalSerializer):
    submitter = EmailUserSerializer()
    applicant = serializers.CharField(source='applicant.organisation.name')
    processing_status = serializers.SerializerMethodField(read_only=True)
    review_status = serializers.SerializerMethodField(read_only=True)
    customer_status = serializers.SerializerMethodField(read_only=True)
    #assigned_officer = serializers.CharField(source='assigned_officer.get_full_name')
    assigned_officer = serializers.SerializerMethodField(read_only=True)

    application_type = serializers.CharField(source='application_type.name', read_only=True)
    #region = serializers.CharField(source='region.name', read_only=True)
    #district = serializers.CharField(source='district.name', read_only=True)
    region = serializers.SerializerMethodField(read_only=True)
    district = serializers.SerializerMethodField(read_only=True)

    #tenure = serializers.CharField(source='tenure.name', read_only=True)
    assessor_process = serializers.SerializerMethodField(read_only=True)
    relevant_applicant_name = serializers.SerializerMethodField(read_only=True)
    apiary_group_application_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Proposal
        fields = (
                'id',
                'application_type',
                'activity',
                'approval_level',
                'title',
                'region',
                'district',
                'tenure',
                'customer_status',
                'processing_status',
                'review_status',
                'applicant',
                'proxy_applicant',
                'submitter',
                'assigned_officer',
                'previous_application',
                'get_history',
                'lodgement_date',
                'modified_date',
                'readonly',
                'can_user_edit',
                'can_user_view',
                'reference',
                'lodgement_number',
                'lodgement_sequence',
                'can_officer_process',
                'assessor_process',
                'allowed_assessors',
                'proposal_type',
                'fee_invoice_reference',
                'fee_paid',
                'relevant_applicant_name',
                'apiary_group_application_type',
                )
        # the serverSide functionality of datatables is such that only columns that have field 'data' defined are requested from the serializer. We
        # also require the following additional fields for some of the mRender functions
        datatables_always_serialize = (
                'id',
                'activity',
                'title',
                'region',
                'customer_status',
                'processing_status',
                'applicant',
                'submitter',
                'assigned_officer',
                'lodgement_date',
                'can_user_edit',
                'can_user_view',
                'reference',
                'lodgement_number',
                'can_officer_process',
                'assessor_process',
                'allowed_assessors',
                'fee_invoice_reference',
                'fee_paid',
                'application_type',
                'relevant_applicant_name',
                'apiary_group_application_type',
                )
    def get_relevant_applicant_name(self,obj):
        return obj.relevant_applicant_name

    def get_assigned_officer(self,obj):
        if obj.assigned_officer:
            return obj.assigned_officer.get_full_name()
        return None

    def get_region(self,obj):
        if obj.region:
            return obj.region.name
        return None

    def get_district(self,obj):
        if obj.district:
            return obj.district.name
        return None

    def get_assessor_process(self,obj):
        # Check if currently logged in user has access to process the proposal
        request = self.context['request']
        user = request.user
        if obj.can_officer_process:
            '''if (obj.assigned_officer and obj.assigned_officer == user) or (user in obj.allowed_assessors):
                return True'''
            if obj.assigned_officer:
                if obj.assigned_officer == user:
                    return True
            elif user in obj.allowed_assessors:
                return True
        return False

    def get_apiary_group_application_type(self, obj):
        return obj.apiary_group_application_type


class ProposalSerializer(BaseProposalSerializer):
    submitter = serializers.CharField(source='submitter.get_full_name')
    processing_status = serializers.SerializerMethodField(read_only=True)
    review_status = serializers.SerializerMethodField(read_only=True)
    customer_status = serializers.SerializerMethodField(read_only=True)

    application_type = serializers.CharField(source='application_type.name', read_only=True)
    #region = serializers.CharField(source='region.name', read_only=True)
    #district = serializers.CharField(source='district.name', read_only=True)
    #tenure = serializers.CharField(source='tenure.name', read_only=True)
    comment_data= serializers.SerializerMethodField(read_only=True)

    proposal_apiary = serializers.SerializerMethodField()
    apiary_temporary_use = ProposalApiaryTemporaryUseSerializer(many=False, read_only=True)
    # apiary_temporary_use_set = ProposalApiaryTemporaryUseSerializer(many=True, read_only=True)
    apiary_group_application_type = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = BaseProposalSerializer.Meta.fields + (
            'comment_data',
            'proposal_apiary',
            'apiary_temporary_use',
            'apiary_group_application_type',
            # 'apiary_temporary_use_set',
        )

    def get_readonly(self,obj):
        return obj.can_user_view

    def get_comment_data(self,obj):
         return obj.comment_data

    def get_proposal_apiary(self, obj):
        if hasattr(obj, 'proposal_apiary'):
            pasl = obj.proposal_apiary
            return ProposalApiarySerializer(pasl).data
        else:
            return ''

    def get_apiary_group_application_type(self, obj):
        return obj.apiary_group_application_type


class SaveProposalSerializer(BaseProposalSerializer):
    assessor_data = serializers.JSONField(required=False)

    class Meta:
        model = Proposal
        fields = (
                'id',
                'application_type',
                'activity',
                'approval_level',
                'title',
                'region',
                'district',
                'tenure',
                'data',
                'assessor_data',
                'comment_data',
                'schema',
                'customer_status',
                'processing_status',
                'review_status',
                #'hard_copy',
                'applicant',
                'proxy_applicant',
                'submitter',
                'assigned_officer',
                'previous_application',
                'lodgement_date',
                'documents',
                'requirements',
                'readonly',
                'can_user_edit',
                'can_user_view',
                'reference',
                'lodgement_number',
                'lodgement_sequence',
                'can_officer_process',
                'sub_activity_level1',
                'sub_activity_level2',
                'management_area',
                )
        read_only_fields=('documents','requirements')

class SaveProposalRegionSerializer(BaseProposalSerializer):

    class Meta:
        model = Proposal
        fields = (
                'id',
                'region',
                'district',
                'activity',
                'sub_activity_level1',
                'sub_activity_level2',
                'management_area',
                'approval_level',
                )
        #read_only_fields=('documents','requirements')

class ApplicantSerializer(serializers.ModelSerializer):
    from disturbance.components.organisations.serializers import OrganisationAddressSerializer
    address = OrganisationAddressSerializer()
    class Meta:
        model = Organisation
        fields = (
                    'id',
                    'name',
                    'abn',
                    'address',
                    'email',
                    'phone_number',
                )


class InternalProposalSerializer(BaseProposalSerializer):
    applicant = ApplicantSerializer()
    processing_status = serializers.SerializerMethodField(read_only=True)
    review_status = serializers.SerializerMethodField(read_only=True)
    customer_status = serializers.SerializerMethodField(read_only=True)
    submitter = serializers.CharField(source='submitter.get_full_name')
    submitter_email = serializers.CharField(source='submitter.email')
    proposaldeclineddetails = ProposalDeclinedDetailsSerializer()
    #
    assessor_mode = serializers.SerializerMethodField()
    current_assessor = serializers.SerializerMethodField()
    assessor_data = serializers.SerializerMethodField()
    latest_referrals = ProposalReferralSerializer(many=True)
    allowed_assessors = EmailUserSerializer(many=True)
    approval_level_document = serializers.SerializerMethodField()
    application_type = serializers.CharField(source='application_type.name', read_only=True)
    referral_email_list=serializers.SerializerMethodField()
    #region = serializers.CharField(source='region.name', read_only=True)
    #district = serializers.CharField(source='district.name', read_only=True)
    #tenure = serializers.CharField(source='tenure.name', read_only=True)
    apiary_temporary_use = ProposalApiaryTemporaryUseSerializer(many=False, read_only=True)

    class Meta:
        model = Proposal
        fields = (
                'id',
                'application_type',
                'activity',
                'approval_level',
                'approval_level_document',
                'approval_level_comment',
                'region',
                'district',
                'tenure',
                'title',
                'data',
                'schema',
                'customer_status',
                'processing_status',
                'review_status',
                #'hard_copy',
                'applicant',
                'proxy_applicant',
                'submitter',
                'submitter_email',
                'assigned_officer',
                'assigned_approver',
                'previous_application',
                'get_history',
                'lodgement_date',
                'modified_date',
                'documents',
                'requirements',
                'readonly',
                'can_user_edit',
                'can_user_view',
                'documents_url',
                'assessor_mode',
                'current_assessor',
                'assessor_data',
                'comment_data',
                'latest_referrals',
                'allowed_assessors',
                'proposed_issuance_approval',
                'proposed_decline_status',
                'proposaldeclineddetails',
                'permit',
                'reference',
                'lodgement_number',
                'lodgement_sequence',
                'can_officer_process',
                'proposal_type',
                'hasAmendmentRequest',
                'referral_email_list',
                'sub_activity_level1',
                'sub_activity_level2',
                'management_area',
                'fee_invoice_reference',
                'fee_paid',
                'apiary_temporary_use',
                )
        read_only_fields=('documents','requirements')

    def get_approval_level_document(self,obj):
        if obj.approval_level_document is not None:
            return [obj.approval_level_document.name,obj.approval_level_document._file.url]
        else:
            return obj.approval_level_document

    def get_assessor_mode(self,obj):
        # TODO check if the proposal has been accepted or declined
        request = self.context['request']
        user = request.user._wrapped if hasattr(request.user,'_wrapped') else request.user
        return {
            'assessor_mode': True,
            'has_assessor_mode': obj.has_assessor_mode(user),
            'assessor_can_assess': obj.can_assess(user),
            'assessor_level': 'assessor',
            'assessor_box_view': obj.assessor_comments_view(user)
        }

    def get_readonly(self,obj):
        return True

    def get_current_assessor(self,obj):
        return {
            'id': self.context['request'].user.id,
            'name': self.context['request'].user.get_full_name(),
            'email': self.context['request'].user.email
        }

    def get_assessor_data(self,obj):
        return obj.assessor_data

    def get_referral_email_list(self,obj):
        request = self.context['request']
        user = request.user._wrapped if hasattr(request.user,'_wrapped') else request.user
        return obj.referral_email_list(user)



class ReferralProposalSerializer(InternalProposalSerializer):
    def get_assessor_mode(self,obj):
        # TODO check if the proposal has been accepted or declined
        request = self.context['request']
        user = request.user._wrapped if hasattr(request.user,'_wrapped') else request.user
        try:
            referral = Referral.objects.get(proposal=obj,referral=user)
        except:
            referral = None
        return {
            'assessor_mode': True,
            'assessor_can_assess': referral.can_assess_referral(user) if referral else None,
            'assessor_level': 'referral',
            'assessor_box_view': obj.assessor_comments_view(user)
        }

class ReferralWrapperSerializer(serializers.ModelSerializer):
    apiary_referral_exists = serializers.SerializerMethodField()
    class Meta:
        model = Referral
        fields = (
            'id',
            'apiary_referral_exists',
        )

    def get_apiary_referral_exists(self,obj):
        return hasattr(obj, 'apiary_referral')


class ReferralSerializer(serializers.ModelSerializer):
    processing_status = serializers.CharField(source='get_processing_status_display')
    latest_referrals = ProposalReferralSerializer(many=True)
    can_be_completed = serializers.BooleanField()
    class Meta:
        model = Referral
        fields = '__all__'

    def __init__(self,*args,**kwargs):
        super(ReferralSerializer, self).__init__(*args, **kwargs)
        self.fields['proposal'] = ReferralProposalSerializer(context={'request':self.context['request']})

class ProposalUserActionSerializer(serializers.ModelSerializer):
    who = serializers.CharField(source='who.get_full_name')
    class Meta:
        model = ProposalUserAction
        fields = '__all__'

class ProposalLogEntrySerializer(CommunicationLogEntrySerializer):
    documents = serializers.SerializerMethodField()
    class Meta:
        model = ProposalLogEntry
        fields = '__all__'
        read_only_fields = (
            'customer',
        )

    def get_documents(self,obj):
        return [[d.name,d._file.url] for d in obj.documents.all()]

class SendReferralSerializer(serializers.Serializer):
    email = serializers.EmailField()
    text = serializers.CharField(allow_blank=True)

class DTReferralSerializer(serializers.ModelSerializer):
    processing_status = serializers.CharField(source='proposal.get_processing_status_display')
    referral_status = serializers.CharField(source='get_processing_status_display')
    proposal_lodgement_date = serializers.CharField(source='proposal.lodgement_date')
    proposal_lodgement_number = serializers.CharField(source='proposal.lodgement_number')
    submitter = serializers.SerializerMethodField()
    region = serializers.CharField(source='region.name', read_only=True)
    referral = EmailUserSerializer()
    relevant_applicant_name = serializers.SerializerMethodField()
    #proposal_application_type = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = (
            'id',
            'region',
            'activity',
            'title',
            #'applicant',
            'relevant_applicant_name',
            'submitter',
            'processing_status',
            'referral_status',
            'lodged_on',
            'proposal',
            'can_be_processed',
            'referral',
            'proposal_lodgement_date',
            'proposal_lodgement_number',
            'referral_text',
        )

    def get_submitter(self,obj):
        return EmailUserSerializer(obj.proposal.submitter).data

    def get_relevant_applicant_name(self,obj):
        return obj.proposal.relevant_applicant_name

class ProposalRequirementSerializer(serializers.ModelSerializer):
    due_date = serializers.DateField(input_formats=['%d/%m/%Y'],required=False,allow_null=True)
    class Meta:
        model = ProposalRequirement
        fields = ('id','due_date','free_requirement','standard_requirement','standard','order','proposal','recurrence','recurrence_schedule','recurrence_pattern','requirement','is_deleted','copied_from')
        read_only_fields = ('order','requirement', 'copied_from')

class ProposalStandardRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalStandardRequirement
        fields = ('id','code','text')

class ProposedApprovalSerializer(serializers.Serializer):
    expiry_date = serializers.DateField(input_formats=['%d/%m/%Y'])
    start_date = serializers.DateField(input_formats=['%d/%m/%Y'])
    details = serializers.CharField()
    cc_email = serializers.CharField(required=False,allow_null=True, allow_blank=True)

class PropedDeclineSerializer(serializers.Serializer):
    reason = serializers.CharField()
    cc_email = serializers.CharField(required=False, allow_null=True)

class AmendmentRequestDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmendmentRequestDocument
        fields = ('id', 'name', '_file')
        #fields = '__all__'

class AmendmentRequestSerializer(serializers.ModelSerializer):
    #reason = serializers.SerializerMethodField()
    amendment_request_documents = AmendmentRequestDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = AmendmentRequest
        fields = '__all__'

    #def get_reason (self,obj):
        #return obj.get_reason_display()
        #return obj.reason.reason

class AmendmentRequestDisplaySerializer(serializers.ModelSerializer):
    reason = serializers.SerializerMethodField()
    amendment_request_documents = AmendmentRequestDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = AmendmentRequest
        fields = '__all__'

    def get_reason (self,obj):
        #return obj.get_reason_display()
        return obj.reason.reason if obj.reason else None


class SearchKeywordSerializer(serializers.Serializer):
    number = serializers.CharField()
    id = serializers.IntegerField()
    type = serializers.CharField()
    applicant = serializers.CharField()
    #text = serializers.CharField(required=False,allow_null=True)
    text = serializers.JSONField(required=False)

class SearchReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
