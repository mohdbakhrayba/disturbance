from django.conf import settings
from ledger.accounts.models import EmailUser,Address

from disturbance.components.approvals.models import (
    Approval,
    ApprovalLogEntry,
    ApprovalUserAction
)
from disturbance.components.organisations.models import (
                                Organisation
                            )
from disturbance.components.main.serializers import CommunicationLogEntrySerializer
from rest_framework import serializers

from disturbance.components.proposals.serializers_apiary import (
    ApplicantAddressSerializer, ApiarySiteSerializer,
)


class EmailUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailUser
        fields = ('id','email','first_name','last_name','title','organisation')


class ApprovalWrapperSerializer(serializers.ModelSerializer):

    class Meta:
        model = Approval
        fields = (
            'id',
            'apiary_approval',
            )


from disturbance.components.proposals.serializers import ProposalSerializer
class ApprovalSerializer(serializers.ModelSerializer):
    #applicant = serializers.CharField(source='applicant.name')
    #applicant_id = serializers.ReadOnlyField(source='applicant.id')
    applicant = serializers.SerializerMethodField(read_only=True)
    applicant_type = serializers.SerializerMethodField(read_only=True)
    applicant_id = serializers.SerializerMethodField(read_only=True)
    licence_document = serializers.CharField(source='licence_document._file.url')
    #renewal_document = serializers.CharField(source='renewal_document._file.url')
    renewal_document = serializers.SerializerMethodField(read_only=True)
    status = serializers.CharField(source='get_status_display')
    allowed_assessors = EmailUserSerializer(many=True)
    region = serializers.CharField(source='current_proposal.region.name')
    district = serializers.CharField(source='current_proposal.district.name', allow_null=True)
    #tenure = serializers.CharField(source='current_proposal.tenure.name')
    activity = serializers.CharField(source='current_proposal.activity')
    title = serializers.CharField(source='current_proposal.title')
    #current_proposal = InternalProposalSerializer(many=False)
    can_approver_reissue = serializers.SerializerMethodField(read_only=True)
    application_type = serializers.SerializerMethodField(read_only=True)

    # apiary_site_location = serializers.SerializerMethodField()
    current_proposal = ProposalSerializer()
    organisation_name = serializers.SerializerMethodField()
    organisation_abn =serializers.SerializerMethodField()
    applicant_first_name =serializers.SerializerMethodField()
    applicant_last_name = serializers.SerializerMethodField()
    applicant_address = serializers.SerializerMethodField()
    apiary_sites = ApiarySiteSerializer(many=True, read_only=True)

    class Meta:
        model = Approval
        fields = (
            'id',
            'lodgement_number',
            'licence_document',
            'replaced_by',
            'current_proposal',
            'activity',
            'region',
            'district',
            'tenure',
            'title',
            'renewal_document',
            'renewal_sent',
            'issue_date',
            'original_issue_date',
            'start_date',
            'expiry_date',
            'surrender_details',
            'suspension_details',
            'applicant',
            'applicant_type',
            'applicant_id',
            'extracted_fields',
            'status',
            'reference',
            'can_reissue',
            'allowed_assessors',
            'cancellation_date',
            'cancellation_details',
            'applicant_id',
            'can_action',
            'set_to_cancel',
            'set_to_surrender',
            'set_to_suspend',
            'can_renew',
            'can_amend',
            'can_reinstate', 
            'can_approver_reissue',
            # 'apiary_site_location',
            'application_type',
            'current_proposal',
            'apiary_approval',
            'organisation_name',
            'organisation_abn',
            'applicant_first_name',
            'applicant_last_name',
            'applicant_address',
            'apiary_sites',
        )
        # the serverSide functionality of datatables is such that only columns that have field 'data' defined are requested from the serializer. We
        # also require the following additional fields for some of the mRender functions
        datatables_always_serialize = (
            'id',
            'activity',
            'region',
            'title',
            'status',
            'reference',
            'lodgement_number',
            'licence_document',
            'start_date',
            'expiry_date',
            'applicant',
            'can_reissue',
            'can_action',
            'can_reinstate',
            'can_amend',
            'can_renew',
            'set_to_cancel',
            'set_to_suspend',
            'set_to_surrender',
            'current_proposal',
            'renewal_document',
            'renewal_sent',
            'allowed_assessors',
            'can_approver_reissue',
        )

    def get_application_type(self,obj):
        if obj.current_proposal.application_type:
            return obj.current_proposal.application_type.name
        return None

    def get_applicant(self,obj):
        try:
            if obj.proxy_applicant and obj.proxy_applicant.get_full_name():
                return obj.proxy_applicant.get_full_name()
            else:
                return obj.applicant.name if isinstance(obj.applicant, Organisation) else obj.applicant
        except:
            return None

    def get_applicant_type(self,obj):
        try:
            return obj.applicant_type
        except:
            return None

    def get_applicant_id(self,obj):
        try:
            return obj.relevant_applicant_id
        except:
            return None

    def get_organisation_name(self,obj):
        if obj.applicant:
            return obj.applicant.name

    def get_organisation_abn(self,obj):
        if obj.applicant:
            return obj.applicant.abn

    def get_applicant_first_name(self,obj):
        if obj.proxy_applicant:
            return obj.proxy_applicant.first_name

    def get_applicant_last_name(self,obj):
        if obj.proxy_applicant:
            return obj.proxy_applicant.last_name

    #def get_relevant_applicant_address(self,obj):
     #   return obj.relevant_applicant_address

    def get_applicant_address(self, obj):
        address_serializer = None
        if obj.relevant_applicant_address:
            address_serializer = ApplicantAddressSerializer(obj.relevant_applicant_address)
            return address_serializer.data
        return address_serializer

    def get_renewal_document(self,obj):
        if obj.renewal_document and obj.renewal_document._file:
            return obj.renewal_document._file.url
        return None

    def get_can_approver_reissue(self,obj):
        # Check if currently logged in user has access to process the proposal
        request = self.context['request']
        user = request.user
        if obj.can_reissue:
            if user in obj.allowed_approvers:
                return True
        return False

    # def get_apiary_site_location(self, obj):
    #     if hasattr(obj.current_proposal, 'apiary_site_location'):
    #         pasl = obj.current_proposal.apiary_site_location
    #         return ProposalApiarySiteLocationSerializer(pasl).data
    #     else:
    #         return ''


class ApprovalCancellationSerializer(serializers.Serializer):
    cancellation_date = serializers.DateField(input_formats=['%d/%m/%Y'])
    cancellation_details = serializers.CharField()

class ApprovalSuspensionSerializer(serializers.Serializer):
    from_date = serializers.DateField(input_formats=['%d/%m/%Y'])
    to_date = serializers.DateField(input_formats=['%d/%m/%Y'], required=False, allow_null=True)
    suspension_details = serializers.CharField()

class ApprovalSurrenderSerializer(serializers.Serializer):
    surrender_date = serializers.DateField(input_formats=['%d/%m/%Y'])
    surrender_details = serializers.CharField()

class ApprovalUserActionSerializer(serializers.ModelSerializer):
    who = serializers.CharField(source='who.get_full_name')
    class Meta:
        model = ApprovalUserAction
        fields = '__all__'

class ApprovalLogEntrySerializer(CommunicationLogEntrySerializer):
    documents = serializers.SerializerMethodField()
    class Meta:
        model = ApprovalLogEntry
        fields = '__all__'
        read_only_fields = (
            'customer',
        )

    def get_documents(self,obj):
        return [[d.name,d._file.url] for d in obj.documents.all()]
