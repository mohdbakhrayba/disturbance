import re
import traceback
import os
import base64
import geojson
import json

import pytz
from ledger.settings_base import TIME_ZONE
from six.moves.urllib.parse import urlparse
from wsgiref.util import FileWrapper
from django.db.models import Q, Min
from django.db import transaction
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import viewsets, serializers, status, generics, views
from rest_framework.decorators import detail_route, list_route, renderer_classes, parser_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework.pagination import PageNumberPagination
from collections import OrderedDict
from django.core.cache import cache
from ledger.accounts.models import EmailUser, Address
from ledger.address.models import Country
from datetime import datetime, timedelta, date

from disturbance.components.main.decorators import basic_exception_handler
from disturbance.components.proposals.utils import (
    save_proponent_data,
    save_assessor_data,
    save_apiary_assessor_data, update_proposal_apiary_temporary_use,
)
from disturbance.components.proposals.models import searchKeyWords, search_reference, ProposalUserAction, \
    ProposalApiary, OnSiteInformation, ApiarySite, ApiaryApplicantChecklistQuestion, ApiaryApplicantChecklistAnswer, \
    ProposalApiaryTemporaryUse, TemporaryUseApiarySite
from disturbance.utils import missing_required_fields, search_tenure, convert_moment_str_to_python_datetime_obj
from disturbance.components.main.utils import check_db_connection, convert_utc_time_to_local

from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from disturbance.components.main.models import Document, Region, District, Tenure, ApplicationType
from disturbance.components.proposals.models import (
    ProposalType,
    Proposal,
    ProposalDocument,
    Referral,
    ProposalRequirement,
    ProposalStandardRequirement,
    AmendmentRequest,
    AmendmentReason,
    AmendmentRequestDocument,
    ApiaryReferralGroup,
    ProposalApiary,
    ApiaryReferral,
)
from disturbance.components.proposals.serializers import (
    SendReferralSerializer,
    ProposalTypeSerializer,
    ProposalSerializer,
    InternalProposalSerializer,
    SaveProposalSerializer,
    DTProposalSerializer,
    ProposalUserActionSerializer,
    ProposalLogEntrySerializer,
    DTReferralSerializer,
    ReferralSerializer,
    ReferralProposalSerializer,
    ProposalRequirementSerializer,
    ProposalStandardRequirementSerializer,
    ProposedApprovalSerializer,
    PropedDeclineSerializer,
    AmendmentRequestSerializer,
    SearchReferenceSerializer,
    SearchKeywordSerializer,
    ListProposalSerializer,
    AmendmentRequestDisplaySerializer,
    SaveProposalRegionSerializer,
    ProposalWrapperSerializer,
    ReferralWrapperSerializer,
)
from disturbance.components.proposals.serializers_base import ProposalReferralSerializer
from disturbance.components.proposals.serializers_apiary import (
    ProposalApiaryTypeSerializer,
    ApiaryInternalProposalSerializer,
    ProposalApiarySerializer,
    SaveProposalApiarySerializer,
    ProposalApiaryTemporaryUseSerializer,
    ProposalApiarySiteTransferSerializer,
    OnSiteInformationSerializer,
    ApiaryReferralGroupSerializer,
    ApiarySiteSerializer,
    SendApiaryReferralSerializer,
    ApiaryReferralSerializer,
    TemporaryUseApiarySiteSerializer,
    DTApiaryReferralSerializer,
    FullApiaryReferralSerializer,
    ProposalHistorySerializer,

)
from disturbance.components.approvals.models import Approval
from disturbance.components.approvals.serializers import ApprovalSerializer
from disturbance.components.compliances.models import Compliance
from disturbance.components.compliances.serializers import ComplianceSerializer

from disturbance.helpers import is_customer, is_internal
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework_datatables.pagination import DatatablesPageNumberPagination
from rest_framework_datatables.filters import DatatablesFilterBackend
from rest_framework_datatables.renderers import DatatablesRenderer
from rest_framework.filters import BaseFilterBackend
from disturbance.components.main.process_document import (
        process_generic_document, 
        #save_comms_log_document_obj
        )

import logging
logger = logging.getLogger(__name__)


class GetProposalType(views.APIView):
    renderer_classes = [JSONRenderer, ]

    def get(self, request, format=None):
        _type = ProposalType.objects.first()
        if _type:
            serializer = ProposalTypeSerializer(_type)
            return Response(serializer.data)
        else:
            return Response({'error': 'There is currently no proposal type.'}, status=status.HTTP_404_NOT_FOUND)

class GetEmptyList(views.APIView):
    renderer_classes = [JSONRenderer, ]

    def get(self, request, format=None):
        return Response([])

#class DatatablesFilterBackend(BaseFilterBackend):
#
#	def filter_queryset(self, request, queryset, view):
#		queryset = super(DatatablesFilterBackend, self).filter_queryset(request, queryset, view)
#		import ipdb; ipdb.set_trace()
#		return queryset

class ProposalFilterBackend(DatatablesFilterBackend):
    """
    Custom filters
    """

    def filter_queryset(self, request, queryset, view):
        total_count = queryset.count()

        def get_choice(status, choices=Proposal.PROCESSING_STATUS_CHOICES):
            for i in choices:
                if i[1]==status:
                    return i[0]
            return None

        #import ipdb; ipdb.set_trace()
        # on the internal dashboard, the Region filter is multi-select - have to use the custom filter below
        regions = request.GET.get('regions')
        if regions:
            if queryset.model is Proposal:
                queryset = queryset.filter(region__name__iregex=regions.replace(',', '|'))
            elif queryset.model is Referral or queryset.model is Compliance:
                queryset = queryset.filter(proposal__region__name__iregex=regions.replace(',', '|'))
            #elif queryset.model is Approval:
            #    queryset = queryset.filter(region__iregex=regions.replace(',', '|'))

        # since in proposal_datatables.vue, the 'region' data field is declared 'searchable=false'
        #global_search = request.GET.get('search[value]')
        #if global_search:
        #    queryset = queryset.filter(region__name__iregex=global_search)


        # on the internal dashboard, the Referral 'Status' filter - have to use the custom filter below
        #import ipdb; ipdb.set_trace()
#        processing_status = request.GET.get('processing_status')
#        processing_status = get_choice(processing_status, Proposal.PROCESSING_STATUS_CHOICES)
#        if processing_status:
#            if queryset.model is Referral:
#                #processing_status_id = [i for i in Proposal.PROCESSING_STATUS_CHOICES if i[1]==processing_status][0][0]
#                queryset = queryset.filter(processing_status=processing_status)

        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        #import ipdb; ipdb.set_trace()
        if queryset.model is Proposal:
            if date_from:
                queryset = queryset.filter(lodgement_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(lodgement_date__lte=date_to)
        elif queryset.model is Approval:
            if date_from:
                queryset = queryset.filter(start_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(expiry_date__lte=date_to)
        elif queryset.model is Compliance:
            if date_from:
                queryset = queryset.filter(due_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(due_date__lte=date_to)

            if request.GET.get('processing_status'):
                queryset = queryset.filter(processing_status__icontains=request.GET.get('processing_status'))

            if request.GET.get('customer_status'):
                queryset = queryset.filter(customer_status__icontains=request.GET.get('customer_status'))

        elif queryset.model is Referral:
            if date_from:
                queryset = queryset.filter(proposal__lodgement_date__gte=date_from)

            if date_to:
                queryset = queryset.filter(proposal__lodgement_date__lte=date_to)


        queryset = super(ProposalFilterBackend, self).filter_queryset(request, queryset, view)
        setattr(view, '_datatables_total_count', total_count)
        return queryset

class ProposalRenderer(DatatablesRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        #import ipdb; ipdb.set_trace()
        if 'view' in renderer_context and hasattr(renderer_context['view'], '_datatables_total_count'):
            data['recordsTotal'] = renderer_context['view']._datatables_total_count
            #data.pop('recordsTotal')
            #data.pop('recordsFiltered')
        return super(ProposalRenderer, self).render(data, accepted_media_type, renderer_context)

#from django.utils.decorators import method_decorator
#from django.views.decorators.cache import cache_page
class ProposalPaginatedViewSet(viewsets.ModelViewSet):
    #import ipdb; ipdb.set_trace()
    #queryset = Proposal.objects.all()
    #filter_backends = (DatatablesFilterBackend,)
    filter_backends = (ProposalFilterBackend,)
    pagination_class = DatatablesPageNumberPagination
    renderer_classes = (ProposalRenderer,)
    queryset = Proposal.objects.none()
    serializer_class = ListProposalSerializer
    page_size = 10

#    @method_decorator(cache_page(60))
#    def dispatch(self, *args, **kwargs):
#        return super(ListProposalViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        #import ipdb; ipdb.set_trace()
        if is_internal(self.request): #user.is_authenticated():
            return Proposal.objects.all()
        elif is_customer(self.request):
            user_orgs = [org.id for org in user.disturbance_organisations.all()]
            #return  Proposal.objects.filter( Q(applicant_id__in = user_orgs) | Q(submitter = user) )
            return  Proposal.objects.filter( Q(applicant_id__in = user_orgs) | Q(submitter = user) | Q(proxy_applicant = user))
            #queryset =  Proposal.objects.filter(region__isnull=False).filter( Q(applicant_id__in = user_orgs) | Q(submitter = user) )
        return Proposal.objects.none()

#    def filter_queryset(self, request, queryset, view):
#        return self.filter_backends[0]().filter_queryset(self.request, queryset, view)
        #return super(ProposalPaginatedViewSet, self).filter_queryset(request, queryset, view)

#    def list(self, request, *args, **kwargs):
#        response = super(ProposalPaginatedViewSet, self).list(request, args, kwargs)
#
#        # Add extra data to response.data
#        #response.data['regions'] = self.get_queryset().filter(region__isnull=False).values_list('region__name', flat=True).distinct()
#        return response

    @list_route(methods=['GET',])
    def proposals_internal(self, request, *args, **kwargs):
        """
        Used by the internal dashboard

        http://localhost:8499/api/proposal_paginated/proposal_paginated_internal/?format=datatables&draw=1&length=2
        """
        #import ipdb; ipdb.set_trace()
        qs = self.get_queryset()
        #qs = self.filter_queryset(self.request, qs, self)
        qs = self.filter_queryset(qs)

        # on the internal organisations dashboard, filter the Proposal/Approval/Compliance datatables by applicant/organisation
        applicant_id = request.GET.get('org_id')
        if applicant_id:
            qs = qs.filter(applicant_id=applicant_id)

        self.paginator.page_size = qs.count()
        result_page = self.paginator.paginate_queryset(qs, request)
        serializer = ListProposalSerializer(result_page, context={'request':request}, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    @list_route(methods=['GET',])
    def referrals_internal(self, request, *args, **kwargs):
        """
        Used by the internal dashboard

        http://localhost:8499/api/proposal_paginated/referrals_internal/?format=datatables&draw=1&length=2
        """
        #import ipdb; ipdb.set_trace()
        #self.serializer_class = ReferralSerializer
        referral_id_list = []
        qs_r = Referral.objects.filter(referral=request.user) if is_internal(self.request) else Referral.objects.none()
        for r in qs_r:
            referral_id_list.append(r.id)
        #qs = self.filter_queryset(self.request, qs, self)
        # Add Apiary Referrals
        qs_ra = Referral.objects.filter(apiary_referral__referral_group__members=request.user)
        #qs = qs_r.union(qs_ra) if qs_r else qs_ra
        for ar in qs_ra:
            if ar.id not in referral_id_list:
                referral_id_list.append(ar.id)
        qs = Referral.objects.filter(id__in=referral_id_list)
        qs = self.filter_queryset(qs)

        self.paginator.page_size = qs.count()
        result_page = self.paginator.paginate_queryset(qs, request)
        serializer = DTReferralSerializer(result_page, context={'request':request}, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    @list_route(methods=['GET',])
    def proposals_external(self, request, *args, **kwargs):
        """
        Used by the external dashboard

        http://localhost:8499/api/proposal_paginated/proposal_paginated_external/?format=datatables&draw=1&length=2
        """
        qs = self.get_queryset().exclude(processing_status='discarded')
        #qs = self.filter_queryset(self.request, qs, self)
        qs = self.filter_queryset(qs)

        # on the internal organisations dashboard, filter the Proposal/Approval/Compliance datatables by applicant/organisation
        applicant_id = request.GET.get('org_id')
        if applicant_id:
            qs = qs.filter(applicant_id=applicant_id)

        #import ipdb; ipdb.set_trace()
        self.paginator.page_size = qs.count()
        result_page = self.paginator.paginate_queryset(qs, request)
        serializer = ListProposalSerializer(result_page, context={'request':request}, many=True)
        return self.paginator.get_paginated_response(serializer.data)


class OnSiteInformationViewSet(viewsets.ModelViewSet):
    queryset = OnSiteInformation.objects.filter(datetime_deleted=None)
    serializer_class = OnSiteInformationSerializer

    @staticmethod
    def sanitize_date(data_dict, property_name):
        if property_name not in data_dict or not data_dict[property_name] or 'invalid' in data_dict[property_name].lower():
            # There isn't 'property_name' in the data received, or
            # the value in it is False, or
            # the value has a substring 'invalid' in it
            # Add the property if needed and set the value to None
            data_dict[property_name] = None
        else:
            # There is a 'property_name' in the data received
            m = re.match('^(\d{2}).(\d{2}).(\d{4})$', data_dict[property_name])
            if m:
                year = m.group(3)
                if int(m.group(2)) > 12:
                    # Date format is 'MM/DD/YYYY' probably
                    month = m.group(1)
                    day = m.group(2)
                else:
                    # Date format is 'DD/MM/YYYY' probably
                    month = m.group(2)
                    day = m.group(1)

                data_dict[property_name] = year + '-' + month + '-' + day
            else:
                # Probably all file
                pass

        return data_dict

    @basic_exception_handler
    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()

            now = datetime.now(pytz.timezone(TIME_ZONE))
            serializer = OnSiteInformationSerializer(instance, {'datetime_deleted': now}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({})

    @basic_exception_handler
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()
            request_data = request.data

            self.sanitize_date(request_data, 'period_from')
            self.sanitize_date(request_data, 'period_to')

            serializer = OnSiteInformationSerializer(instance, data=request_data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @basic_exception_handler
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            request_data = request.data

            self.sanitize_date(request_data, 'period_from')
            self.sanitize_date(request_data, 'period_to')

            serializer = OnSiteInformationSerializer(data=request_data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class ApiarySiteViewSet(viewsets.ModelViewSet):
    queryset = ApiarySite.objects.all()
    serializer_class = ApiarySiteSerializer

    @basic_exception_handler
    def partial_update(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()
            request_data = request.data

            serializer = ApiarySiteSerializer(instance, data=request_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data)


class ProposalApiaryViewSet(viewsets.ModelViewSet):
    queryset = ProposalApiary.objects.none()
    serializer_class = ProposalApiarySerializer

    @detail_route(methods=['GET', ])
    def on_site_information_list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ProposalApiarySerializer(instance)
        return Response(serializer.data)

    def get_queryset(self):
        return ProposalApiary.objects.all()

    @basic_exception_handler
    def internal_apiary_serializer_class(self):
        #import ipdb; ipdb.set_trace()
        #application_type = Proposal.objects.get(id=self.kwargs.get('pk')).application_type.name
        instance = self.get_object()
        application_type = instance.proposal.application_type.name
        if application_type == ApplicationType.APIARY:
            return ApiaryInternalProposalSerializer
            #return InternalProposalSerializer
        else:
            pass
            #return InternalProposalSerializer

    @detail_route(methods=['GET',])
    def internal_apiary_proposal(self, request, *args, **kwargs):
        instance = self.get_object()
        proposal_instance = instance.proposal
        proposal_instance.internal_view_log(request)
        #serializer = InternalProposalSerializer(instance,context={'request':request})
        serializer_class = self.internal_serializer_class()
        serializer = serializer_class(proposal_instance,context={'request':request})
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    @renderer_classes((JSONRenderer,))
    @basic_exception_handler
    def process_deed_poll_document(self, request, *args, **kwargs):
        instance = self.get_object()
        returned_data = process_generic_document(request, instance, document_type='deed_poll_documents')
        if returned_data:
            return Response(returned_data)
        else:
            return Response()

    @detail_route(methods=['post'])
    @basic_exception_handler
    def apiary_assessor_send_referral(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = SendApiaryReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #text=serializer.validated_data['text']
        #instance.send_referral(request,serializer.validated_data['email'])
        #import ipdb; ipdb.set_trace()
        #instance.send_referral(request,serializer.validated_data['email_group'], serializer.validated_data['text'])
        instance.send_referral(request,serializer.validated_data['group_id'], serializer.validated_data['text'])
        serializer_class = self.internal_apiary_serializer_class()
        serializer = serializer_class(instance.proposal,context={'request':request})
        return Response(serializer.data)

    @detail_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    @basic_exception_handler
    def assessor_save(self, request, *args, **kwargs):
        instance = self.get_object()
        save_apiary_assessor_data(
                instance.proposal,
                request,
                self)
        return redirect(reverse('external'))

    @detail_route(methods=['GET', ])
    @renderer_classes((JSONRenderer,))
    def proposal_history(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            proposal_instance = instance.proposal
            #entry_number = request.data.get("running_sheet_entry_number")
            #row_num = entry_number.split('-')[1]
            #entry_instance = instance.running_sheet_entries.get(row_num=row_num)


            serializer = ProposalHistorySerializer(proposal_instance)
            return Response(
                    serializer.data, 
                    status=status.HTTP_200_OK,
                    )
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    @basic_exception_handler
    def final_approval(self, request, *args, **kwargs):
        #import ipdb;ipdb.set_trace()
        instance = self.get_object()
        serializer = ProposedApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.final_approval(request,serializer.validated_data)
        #serializer = InternalProposalSerializer(instance,context={'request':request})
        serializer_class = self.internal_apiary_serializer_class()
        serializer = serializer_class(instance.proposal,context={'request':request})
        return Response(serializer.data)


class ApiaryReferralViewSet(viewsets.ModelViewSet):
    #queryset = Referral.objects.all()
    queryset = ApiaryReferral.objects.none()
    serializer_class = ApiaryReferralSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated() and is_internal(self.request):
            #queryset =  Referral.objects.filter(referral=user)
            queryset =  ApiaryReferral.objects.all()
            return queryset
        return ApiaryReferral.objects.none()

    #@list_route(methods=['GET',])
    #def filter_list(self, request, *args, **kwargs):
    #    """ Used by the external dashboard filters """
    #    qs =  self.get_queryset().filter(referral=request.user)
    #    region_qs =  qs.filter(proposal__region__isnull=False).values_list('proposal__region__name', flat=True).distinct()
    #    #district_qs =  qs.filter(proposal__district__isnull=False).values_list('proposal__district__name', flat=True).distinct()
    #    activity_qs =  qs.filter(proposal__activity__isnull=False).order_by('proposal__activity').distinct('proposal__activity').values_list('proposal__activity', flat=True).distinct()
    #    submitter_qs = qs.filter(proposal__submitter__isnull=False).order_by('proposal__submitter').distinct('proposal__submitter').values_list('proposal__submitter__first_name','proposal__submitter__last_name','proposal__submitter__email')
    #    submitters = [dict(email=i[2], search_term='{} {} ({})'.format(i[0], i[1], i[2])) for i in submitter_qs]
    #    processing_status_qs =  qs.filter(proposal__processing_status__isnull=False).order_by('proposal__processing_status').distinct('proposal__processing_status').values_list('proposal__processing_status', flat=True)
    #    processing_status = [dict(value=i, name='{}'.format(' '.join(i.split('_')).capitalize())) for i in processing_status_qs]
    #    data = dict(
    #        regions=region_qs,
    #        #districts=district_qs,
    #        activities=activity_qs,
    #        submitters=submitters,
    #        processing_status_choices=processing_status,
    #    )
    #    return Response(data)


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request':request})
        return Response(serializer.data)

    @list_route(methods=['GET',])
    def user_list(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(referral__referral=request.user)
        serializer = DTReferralSerializer(qs, many=True)
        #serializer = DTReferralSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @list_route(methods=['GET',])
    def user_group_list(self, request, *args, **kwargs):
        qs = ApiaryReferralGroup.objects.filter().values_list('name', flat=True)
        return Response(qs)

    @list_route(methods=['GET',])
    def datatable_list(self, request, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        proposal_field = request.GET.get('proposal',None)
        proposal = Proposal.objects.get(id=int(proposal_field))
        #qs = self.get_queryset().all()
        if proposal:
            #qs = qs.filter(referral__proposal_id=int(proposal))
            #qs = ApiaryReferral.objects.filter(referral__proposal=proposal).referral
            qs = Referral.objects.filter(proposal=proposal)
        #serializer = DTReferralSerializer(qs, many=True)
        serializer = DTApiaryReferralSerializer(qs, many=True)
        return Response(serializer.data)


    @detail_route(methods=['GET',])
    def referral_list(self, request, *args, **kwargs):
        instance = self.get_object()
        #qs = self.get_queryset().all()
        #qs=qs.filter(sent_by=instance.referral, proposal=instance.proposal)

        qs = ApiaryReferral.objects.filter(
                referral_group__in=request.user.apiaryreferralgroup_set.all(), 
                proposal=instance.referral.proposal
                )
        #serializer = DTReferralSerializer(qs, many=True)
        serializer = ApiaryReferralSerializer(qs, many=True)

        return Response(serializer.data)

    @detail_route(methods=['GET', 'POST'])
    def complete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.complete(request)
            data={}
            data['type']=u'referral_complete'
            data['fromm']=u'{}'.format(instance.referral_group.name)
            data['proposal'] = u'{}'.format(instance.referral.proposal.id)
            data['staff'] = u'{}'.format(request.user.id)
            data['text'] = u'{}'.format(instance.referral.referral_text)
            data['subject'] = u'{}'.format(instance.referral.referral_text)
            serializer = ProposalLogEntrySerializer(data=data)
            serializer.is_valid(raise_exception=True)
            comms = serializer.save()
            #if instance.document:
             #   document = comms.documents.create(_file=instance.document._file, name=instance.document.name)
              #  document.input_name = instance.document.input_name
               # document.can_delete = True
                #document.save()

            serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def remind(self, request, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        try:
            instance = self.get_object()
            instance.remind(request)
            serializer = ApiaryInternalProposalSerializer(instance.referral.proposal,context={'request':request})
            #serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def recall(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.recall(request)
            #serializer = InternalProposalSerializer(instance.proposal,context={'request':request})
            serializer = ApiaryInternalProposalSerializer(instance.referral.proposal,context={'request':request})
            #serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def resend(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.resend(request)
            #serializer = InternalProposalSerializer(instance.proposal,context={'request':request})
            serializer = ApiaryInternalProposalSerializer(instance.referral.proposal,context={'request':request})
            #serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    def send_referral(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = SendApiaryReferralSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            #instance.send_referral(request,serializer.validated_data['email'],serializer.validated_data['text'])
            #instance.send_referral(request,serializer.validated_data['group_id'], serializer.validated_data['text'])
            instance.referral.proposal.proposal_apiary.send_referral(request,serializer.validated_data['group_id'], serializer.validated_data['text'])
            serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class ProposalViewSet(viewsets.ModelViewSet):
    #import ipdb; ipdb.set_trace()
    #queryset = Proposal.objects.all()
    queryset = Proposal.objects.none()
    serializer_class = ProposalSerializer

    def get_queryset(self):
        user = self.request.user
        #import ipdb; ipdb.set_trace()
        if is_internal(self.request): #user.is_authenticated():
            #return Proposal.objects.all()
            return Proposal.objects.filter(region__isnull=False)
        elif is_customer(self.request):
            user_orgs = [org.id for org in user.disturbance_organisations.all()]
            #queryset =  Proposal.objects.filter( Q(applicant_id__in = user_orgs) | Q(submitter = user) )
            queryset =  Proposal.objects.filter(region__isnull=False).filter( Q(applicant_id__in = user_orgs) | Q(submitter = user) )
            return queryset
        logger.warn("User is neither customer nor internal user: {} <{}>".format(user.get_full_name(), user.email))
        return Proposal.objects.none()

    def get_object(self):

        check_db_connection()
        try:
            obj = super(ProposalViewSet, self).get_object()
        except Exception, e:
            # because current queryset excludes migrated licences
            #import ipdb; ipdb.set_trace()
            #obj = get_object_or_404(Proposal, id=self.kwargs['id'])
            obj_id = self.kwargs['id'] if 'id' in self.kwargs else self.kwargs['pk']
            obj = get_object_or_404(Proposal, id=obj_id)
        return obj

    def get_serializer_class(self):
        try:
            application_type = self.get_object().application_type.name
            if application_type == ApplicationType.APIARY:
                return ProposalApiaryTypeSerializer
            else:
                return ProposalSerializer
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def internal_serializer_class(self):
        try:
            #import ipdb; ipdb.set_trace()
            #application_type = Proposal.objects.get(id=self.kwargs.get('pk')).application_type.name
            application_type = self.get_object().application_type.name
            if application_type == ApplicationType.APIARY:
                return ApiaryInternalProposalSerializer
                #return InternalProposalSerializer
            else:
                return InternalProposalSerializer
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST'])
    @renderer_classes((JSONRenderer,))
    def process_deed_poll_document(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            returned_data = process_generic_document(request, instance, document_type='deed_poll_documents')
            if returned_data:
                return Response(returned_data)
            else:
                return Response()

        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e, 'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @list_route(methods=['GET',])
    def filter_list(self, request, *args, **kwargs):
        """ Used by the internal/external dashboard filters """
        region_qs =  self.get_queryset().filter(region__isnull=False).values_list('region__name', flat=True).distinct()
        #district_qs =  self.get_queryset().filter(district__isnull=False).values_list('district__name', flat=True).distinct()
        activity_qs =  self.get_queryset().filter(activity__isnull=False).values_list('activity', flat=True).distinct()
        submitter_qs = self.get_queryset().filter(submitter__isnull=False).distinct('submitter__email').values_list('submitter__first_name','submitter__last_name','submitter__email')
        submitters = [dict(email=i[2], search_term='{} {} ({})'.format(i[0], i[1], i[2])) for i in submitter_qs]
        data = dict(
            regions=region_qs,
            #districts=district_qs,
            activities=activity_qs,
            submitters=submitters,
            #processing_status_choices = [i[1] for i in Proposal.PROCESSING_STATUS_CHOICES],
            #processing_status_id_choices = [i[0] for i in Proposal.PROCESSING_STATUS_CHOICES],
            #customer_status_choices = [i[1] for i in Proposal.CUSTOMER_STATUS_CHOICES],
            approval_status_choices = [i[1] for i in Approval.STATUS_CHOICES],
        )
        return Response(data)

    @detail_route(methods=['POST'])
    @renderer_classes((JSONRenderer,))
    def process_document(self, request, *args, **kwargs):
        try:
            #import ipdb; ipdb.set_trace()
            instance = self.get_object()
            action = request.POST.get('action')
            section = request.POST.get('input_name')
            if action == 'list' and 'input_name' in request.POST:
                pass

            elif action == 'delete' and 'document_id' in request.POST:
                document_id = request.POST.get('document_id')
                document = instance.documents.get(id=document_id)

                if document._file and os.path.isfile(document._file.path) and document.can_delete:
                    os.remove(document._file.path)

                document.delete()
                instance.save(version_comment='Approval File Deleted: {}'.format(document.name)) # to allow revision to be added to reversion history
                #instance.current_proposal.save(version_comment='File Deleted: {}'.format(document.name)) # to allow revision to be added to reversion history

            elif action == 'hide' and 'document_id' in request.POST:
                document_id = request.POST.get('document_id')
                document = instance.documents.get(id=document_id)

                document.hidden=True
                document.save()
                instance.save(version_comment='File hidden: {}'.format(document.name)) # to allow revision to be added to reversion history

            elif action == 'save' and 'input_name' in request.POST and 'filename' in request.POST:
                proposal_id = request.POST.get('proposal_id')
                filename = request.POST.get('filename')
                _file = request.POST.get('_file')
                if not _file:
                    _file = request.FILES.get('_file')

                document = instance.documents.get_or_create(input_name=section, name=filename)[0]
                path = default_storage.save('proposals/{}/documents/{}'.format(proposal_id, filename), ContentFile(_file.read()))

                document._file = path
                #import ipdb; ipdb.set_trace()
                document.save()
                instance.save(version_comment='File Added: {}'.format(filename)) # to allow revision to be added to reversion history
                #instance.current_proposal.save(version_comment='File Added: {}'.format(filename)) # to allow revision to be added to reversion history

            return  Response( [dict(input_name=d.input_name, name=d.name,file=d._file.url, id=d.id, can_delete=d.can_delete, can_hide=d.can_hide) for d in instance.documents.filter(input_name=section, hidden=False) if d._file] )

        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


#    def list(self, request, *args, **kwargs):
#        #import ipdb; ipdb.set_trace()
#        #queryset = self.get_queryset()
#        #serializer = DTProposalSerializer(queryset, many=True)
#        #import ipdb; ipdb.set_trace()
#        #serializer = DTProposalSerializer(self.get_queryset(), many=True)
#        serializer = ListProposalSerializer(self.get_queryset(), context={'request':request}, many=True)
#        return Response(serializer.data)

    @list_route(methods=['GET',])
    def list_paginated(self, request, *args, **kwargs):
        """
        https://stackoverflow.com/questions/29128225/django-rest-framework-3-1-breaks-pagination-paginationserializer
        """
        proposals = self.get_queryset()
        paginator = PageNumberPagination()
        #paginator = LimitOffsetPagination()
        paginator.page_size = 5
        result_page = paginator.paginate_queryset(proposals, request)
        serializer = ListProposalSerializer(result_page, context={'request':request}, many=True)
        return paginator.get_paginated_response(serializer.data)

    @detail_route(methods=['GET',])
    def action_log(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            qs = instance.action_logs.all()
            serializer = ProposalUserActionSerializer(qs,many=True)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def comms_log(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            qs = instance.comms_logs.all()
            serializer = ProposalLogEntrySerializer(qs,many=True)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    @renderer_classes((JSONRenderer,))
    def add_comms_log(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()
                request.data['proposal'] = u'{}'.format(instance.id)
                request.data['staff'] = u'{}'.format(request.user.id)
                serializer = ProposalLogEntrySerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                comms = serializer.save()
                # Save the files
                for f in request.FILES:
                    document = comms.documents.create()
                    document.name = str(request.FILES[f])
                    document._file = request.FILES[f]
                    document.save()
                # End Save Documents

                return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def requirements(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            #qs = instance.requirements.all()
            qs = instance.requirements.all().exclude(is_deleted=True)
            serializer = ProposalRequirementSerializer(qs,many=True)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def amendment_request(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            qs = instance.amendment_requests
            qs = qs.filter(status = 'requested')
            serializer = AmendmentRequestDisplaySerializer(qs,many=True)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @list_route(methods=['GET',])
    def user_list(self, request, *args, **kwargs):
        qs = self.get_queryset().exclude(processing_status='discarded')
        #serializer = DTProposalSerializer(qs, many=True)
        serializer = ListProposalSerializer(qs,context={'request':request}, many=True)
        return Response(serializer.data)

    @list_route(methods=['GET',])
    def user_list_paginated(self, request, *args, **kwargs):
        """
        Placing Paginator class here (instead of settings.py) allows specific method for desired behaviour),
        otherwise all serializers will use the default pagination class

        https://stackoverflow.com/questions/29128225/django-rest-framework-3-1-breaks-pagination-paginationserializer
        """
        proposals = self.get_queryset().exclude(processing_status='discarded')
        paginator = DatatablesPageNumberPagination()
        paginator.page_size = proposals.count()
        result_page = paginator.paginate_queryset(proposals, request)
        serializer = ListProposalSerializer(result_page, context={'request':request}, many=True)
        return paginator.get_paginated_response(serializer.data)

    @list_route(methods=['GET',])
    def list_paginated(self, request, *args, **kwargs):
        """
        Placing Paginator class here (instead of settings.py) allows specific method for desired behaviour),
        otherwise all serializers will use the default pagination class

        https://stackoverflow.com/questions/29128225/django-rest-framework-3-1-breaks-pagination-paginationserializer
        """
        proposals = self.get_queryset()
        paginator = DatatablesPageNumberPagination()
        paginator.page_size = proposals.count()
        result_page = paginator.paginate_queryset(proposals, request)
        serializer = ListProposalSerializer(result_page, context={'request':request}, many=True)
        return paginator.get_paginated_response(serializer.data)

    @detail_route(methods=['GET',])
    def internal_proposal(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.internal_view_log(request)
        #serializer = InternalProposalSerializer(instance,context={'request':request})
        serializer_class = self.internal_serializer_class()
        serializer = serializer_class(instance,context={'request':request})
        return Response(serializer.data)

    @detail_route(methods=['GET',])
    def internal_proposal_wrapper(self, request, *args, **kwargs):
        instance = self.get_object()
        #instance.internal_view_log(request)
        #serializer = InternalProposalSerializer(instance,context={'request':request})
        serializer_class = ProposalWrapperSerializer #self.internal_serializer_class()
        #serializer = serializer_class(instance,context={'request':request})
        serializer = serializer_class(instance)
        return Response(serializer.data)

    @detail_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    def submit(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.apiary_group_application_type:
                save_proponent_data(instance, request, self)
            else:
                instance.submit(request, self)
                instance.tenure = search_tenure(instance)

            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            #return redirect(reverse('external'))
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def assign_request_user(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.assign_officer(request,request.user)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def assign_to(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user_id = request.data.get('assessor_id',None)
            user = None
            if not user_id:
                raise serializers.ValidationError('An assessor id is required')
            try:
                user = EmailUser.objects.get(id=user_id)
            except EmailUser.DoesNotExist:
                raise serializers.ValidationError('A user with the id passed in does not exist')
            instance.assign_officer(request,user)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def unassign(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.unassign(request)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def switch_status(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            status = request.data.get('status')
            approver_comment = request.data.get('approver_comment')
            if not status:
                raise serializers.ValidationError('Status is required')
            else:
                if not status in ['with_assessor','with_assessor_requirements','with_approver']:
                    raise serializers.ValidationError('The status provided is not allowed')
            instance.move_to_status(request,status, approver_comment)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def reissue_approval(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            status = request.data.get('status')
            if not status:
                raise serializers.ValidationError('Status is required')
            else:
                if not status in ['with_approver']:
                    raise serializers.ValidationError('The status provided is not allowed')
            instance.reissue_approval(request,status)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def renew_approval(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance = instance.renew_approval(request)
            serializer = SaveProposalSerializer(instance,context={'request':request})
            return Response(serializer.data)
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e[0].encode('utf-8')))

    @detail_route(methods=['GET',])
    def amend_approval(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance = instance.amend_approval(request)
            serializer = SaveProposalSerializer(instance,context={'request':request})
            return Response(serializer.data)
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e[0].encode('utf-8')))

    @detail_route(methods=['POST',])
    def proposed_approval(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = ProposedApprovalSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance.proposed_approval(request,serializer.validated_data)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def approval_level_document(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance = instance.assing_approval_level_document(request)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def approval_level_comment(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance = instance.save_approval_level_comment(request)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def final_approval(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = ProposedApprovalSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance.final_approval(request,serializer.validated_data)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def proposed_decline(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = PropedDeclineSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance.proposed_decline(request,serializer.validated_data)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    def final_decline(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = PropedDeclineSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance.final_decline(request,serializer.validated_data)
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    def assesor_send_referral(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = SendReferralSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            #text=serializer.validated_data['text']
            #instance.send_referral(request,serializer.validated_data['email'])
            instance.send_referral(request,serializer.validated_data['email'], serializer.validated_data['text'])
            #serializer = InternalProposalSerializer(instance,context={'request':request})
            serializer_class = self.internal_serializer_class()
            serializer = serializer_class(instance,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    def draft(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            save_proponent_data(instance, request, self)
            return redirect(reverse('external'))
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
        raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    def update_region_section(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            region = request.data.get('region')
            district = request.data.get('district')
            activity = request.data.get('activity')
            sub_activity1 = request.data.get('sub_activity1')
            sub_activity2 = request.data.get('sub_activity2')
            management_area = request.data.get('category')
            approval_level = request.data.get('approval_level')
            data={
                'region': region,
                'district': district,
                'activity': activity,
                'sub_activity_level1': sub_activity1,
                'sub_activity_level2': sub_activity2,
                'management_area': management_area,
                'approval_level': approval_level,
            }
            serializer = SaveProposalRegionSerializer(instance,data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
        raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    @renderer_classes((JSONRenderer,))
    def assessor_save(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            save_assessor_data(instance,request,self)
            return redirect(reverse('external'))
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def create(self, request, *args, **kwargs):
        print(request.data)
        #import ipdb; ipdb.set_trace()
        try:
            with transaction.atomic():
                http_status = status.HTTP_200_OK
                application_type = ApplicationType.objects.get(id=request.data.get('application'))

                # When there is a parameter named 'application_type_str', we may need to update application_type
                application_type_str = request.data.get('application_type_str', None)
                if application_type_str == 'temporary_use':
                    application_type = ApplicationType.objects.get(name=ApplicationType.TEMPORARY_USE)
                elif application_type_str == 'site_transfer':
                    application_type = ApplicationType.objects.get(name=ApplicationType.SITE_TRANSFER)

                #region = request.data.get('region') if request.data.get('region') else 1
                region = request.data.get('region')
                district = request.data.get('district')
                activity = request.data.get('activity')
                sub_activity1 = request.data.get('sub_activity1')
                sub_activity2 = request.data.get('sub_activity2')
                category = request.data.get('category')
                approval_level = request.data.get('approval_level')

                # Get most recent versions of the Proposal Types
                qs_proposal_type = ProposalType.objects.all().order_by('name', '-version').distinct('name')
                proposal_type = qs_proposal_type.get(name=application_type.name)
                applicant = None
                proxy_applicant = None
                if request.data.get('behalf_of') == 'individual':
                    # Validate User for Individual applications
                    request_user = EmailUser.objects.get(id=request.user.id)
                    if not request_user.residential_address:
                        raise ValidationError('null_applicant_address')
                    # Assign request.user as applicant
                    proxy_applicant = request.user.id
                else:
                    applicant = request.data.get('behalf_of')

                data = {
                    #'schema': qs_proposal_type.order_by('-version').first().schema,
                    'schema': proposal_type.schema,
                    'submitter': request.user.id,
                    'applicant': applicant,
                    'proxy_applicant': proxy_applicant,
                    'application_type': application_type.id,
                    'region': region,
                    'district': district,
                    'activity': activity,
                    'approval_level': approval_level,
                    'sub_activity_level1':sub_activity1,
                    'sub_activity_level2':sub_activity2,
                    'management_area':category,
                    'data': [
                    ],
                }
                serializer = SaveProposalSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                proposal_obj = serializer.save()

                # TODO any APIARY specific settings go here - eg renewal, amendment
                details_data = {
                    'proposal_id': proposal_obj.id
                }
                if application_type.name == ApplicationType.APIARY:
                    serializer = SaveProposalApiarySerializer(data=details_data)
                    serializer.is_valid(raise_exception=True)
                    proposal_apiary = serializer.save()
                    for question in ApiaryApplicantChecklistQuestion.objects.all():
                        new_answer = ApiaryApplicantChecklistAnswer.objects.create(proposal = proposal_apiary,
                                                                                   question = question)

                elif application_type.name == ApplicationType.TEMPORARY_USE:
                    approval_id = request.data.get('approval_id')
                    approval = Approval.objects.get(id=approval_id)

                    # # format from_date
                    # from_datetime = convert_utc_time_to_local(apiary_temp_use['from_date'])
                    # from_date = from_datetime.date() if from_datetime else None
                    #
                    # # format to_date
                    # to_datetime = convert_utc_time_to_local(apiary_temp_use['to_date'])
                    # to_date = to_datetime.date() if to_datetime else None
                    #
                    # details_data['from_date'] = from_date
                    # details_data['to_date'] = to_date
                    # details_data['temporary_occupier_name'] = apiary_temp_use['temporary_occupier_name']
                    # details_data['temporary_occupier_phone'] = apiary_temp_use['temporary_occupier_phone']
                    # details_data['temporary_occupier_mobile'] = apiary_temp_use['temporary_occupier_mobile']
                    # details_data['temporary_occupier_email'] = apiary_temp_use['temporary_occupier_email']
                    # # details_data['proposal_apiary_base_id'] = apiary_temp_use['proposal_apiary_base_id']
                    #
                    # Save ProposalApiaryTemporaryUse

                    details_data['loaning_approval_id'] = approval_id
                    serializer = ProposalApiaryTemporaryUseSerializer(data=details_data)
                    serializer.is_valid(raise_exception=True)
                    new_temp_use = serializer.save()

                    # Save TemporaryUseApiarySite
                    for site_approval in approval.apiary_site_approval_set.all():
                        data_to_save = {
                            'proposal_apiary_temporary_use_id': new_temp_use.id,
                            'apiary_site_id': site_approval.apiary_site.id,
                        }
                        serializer = TemporaryUseApiarySiteSerializer(data=data_to_save)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

                elif application_type.name == ApplicationType.SITE_TRANSFER:
                    serializer = ProposalApiarySiteTransferSerializer(data=details_data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                else:
                    pass

                serializer = SaveProposalSerializer(proposal_obj)
                return Response(serializer.data)
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        try:
            http_status = status.HTTP_200_OK
            application_type = ApplicationType.objects.get(id=request.data.get('application'))

            # When there is a parameter named 'application_type_str', we may need to update application_type
            application_type_str = request.data.get('application_type_str', None)
            if application_type_str == 'temporary_use':
                application_type = ApplicationType.objects.get(name=ApplicationType.TEMPORARY_USE)
            elif application_type_str == 'site_transfer':
                application_type = ApplicationType.objects.get(name=ApplicationType.SITE_TRANSFER)

            if application_type.name == ApplicationType.APIARY:
                pass
                # TODO Update new apiary application

            elif application_type.name == ApplicationType.TEMPORARY_USE:
                # Proposal obj should not be changed
                # Only ProposalApiaryTemporaryUse object needs to be updated
                apiary_temporary_use_obj = ProposalApiaryTemporaryUse.objects.get(id=request.data.get('apiary_temporary_use')['id'])
                apiary_temporary_use_data = request.data.get('apiary_temporary_use')
                update_proposal_apiary_temporary_use(apiary_temporary_use_obj, apiary_temporary_use_data)

                proposal_obj = self.get_object()
                serializer = ProposalSerializer(proposal_obj)
                return Response(serializer.data)

            elif application_type.name == ApplicationType.SITE_TRANSFER:
                pass
                # TODO update Site Transfer Application

            instance = self.get_object()
            serializer = SaveProposalSerializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def destroy(self, request,*args,**kwargs):
        try:
            http_status = status.HTTP_200_OK
            instance = self.get_object()
            serializer = SaveProposalSerializer(instance,{'processing_status':'discarded', 'previous_application': None},partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data,status=http_status)
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class ReferralViewSet(viewsets.ModelViewSet):
    #queryset = Referral.objects.all()
    queryset = Referral.objects.none()
    serializer_class = ReferralSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated() and is_internal(self.request):
            #queryset =  Referral.objects.filter(referral=user)
            queryset =  Referral.objects.all()
            return queryset
        return Referral.objects.none()

    def get_serializer_class(self):
        #import ipdb; ipdb.set_trace()
        try:
            #referral_id = self.kwargs.get('referral_id')
            #if referral_id:
             #   referral = Referral.objects.get(id=referral_id)
            referral = self.get_object()
            apiary_referral_attribute_exists = getattr(referral, 'apiary_referral', None)
            if apiary_referral_attribute_exists:
                return FullApiaryReferralSerializer
            else:
                return ReferralSerializer
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @list_route(methods=['GET',])
    def filter_list(self, request, *args, **kwargs):
        """ Used by the external dashboard filters """
        qs =  self.get_queryset().filter(referral=request.user)
        region_qs =  qs.filter(proposal__region__isnull=False).values_list('proposal__region__name', flat=True).distinct()
        #district_qs =  qs.filter(proposal__district__isnull=False).values_list('proposal__district__name', flat=True).distinct()
        activity_qs =  qs.filter(proposal__activity__isnull=False).order_by('proposal__activity').distinct('proposal__activity').values_list('proposal__activity', flat=True).distinct()
        submitter_qs = qs.filter(proposal__submitter__isnull=False).order_by('proposal__submitter').distinct('proposal__submitter').values_list('proposal__submitter__first_name','proposal__submitter__last_name','proposal__submitter__email')
        submitters = [dict(email=i[2], search_term='{} {} ({})'.format(i[0], i[1], i[2])) for i in submitter_qs]
        processing_status_qs =  qs.filter(proposal__processing_status__isnull=False).order_by('proposal__processing_status').distinct('proposal__processing_status').values_list('proposal__processing_status', flat=True)
        processing_status = [dict(value=i, name='{}'.format(' '.join(i.split('_')).capitalize())) for i in processing_status_qs]
        data = dict(
            regions=region_qs,
            #districts=district_qs,
            activities=activity_qs,
            submitters=submitters,
            processing_status_choices=processing_status,
        )
        return Response(data)

    @detail_route(methods=['GET',])
    def referral_wrapper(self, request, *args, **kwargs):
        instance = self.get_object()
        #instance.internal_view_log(request)
        #serializer = InternalProposalSerializer(instance,context={'request':request})
        serializer_class = ReferralWrapperSerializer #self.internal_serializer_class()
        #serializer = serializer_class(instance,context={'request':request})
        serializer = serializer_class(instance)
        return Response(serializer.data)


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request':request})
        #serializer = self.get_serializer_class(request)
        return Response(serializer.data)

    @list_route(methods=['GET',])
    def user_list(self, request, *args, **kwargs):
        qs = self.get_queryset().filter(referral=request.user)
        serializer = DTReferralSerializer(qs, many=True)
        #serializer = DTReferralSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @list_route(methods=['GET',])
    def datatable_list(self, request, *args, **kwargs):
        proposal = request.GET.get('proposal',None)
        qs = self.get_queryset().all()
        if proposal:
            qs = qs.filter(proposal_id=int(proposal))
        serializer = DTReferralSerializer(qs, many=True)
        return Response(serializer.data)

    @detail_route(methods=['GET',])
    def referral_list(self, request, *args, **kwargs):
        instance = self.get_object()
        qs = self.get_queryset().all()
        qs=qs.filter(sent_by=instance.referral, proposal=instance.proposal)
        serializer = DTReferralSerializer(qs, many=True)
        #serializer = ProposalReferralSerializer(qs, many=True)

        return Response(serializer.data)

    @detail_route(methods=['GET', 'POST'])
    def complete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            #import ipdb; ipdb.set_trace()
            referral_comment = request.data.get('referral_comment')
            instance.complete(request, referral_comment)
            serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def remind(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.remind(request)
            serializer = InternalProposalSerializer(instance.proposal,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def recall(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.recall(request)
            serializer = InternalProposalSerializer(instance.proposal,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def resend(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.resend(request)
            serializer = InternalProposalSerializer(instance.proposal,context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    def send_referral(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = SendReferralSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance.send_referral(request,serializer.validated_data['email'],serializer.validated_data['text'])
            serializer = self.get_serializer(instance, context={'request':request})
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class ProposalRequirementViewSet(viewsets.ModelViewSet):
    #queryset = ProposalRequirement.objects.all()
    queryset = ProposalRequirement.objects.none()
    serializer_class = ProposalRequirementSerializer

    def get_queryset(self):
        qs = ProposalRequirement.objects.all().exclude(is_deleted=True)
        return qs

    @detail_route(methods=['GET',])
    def move_up(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.up()
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def move_down(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.down()
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['GET',])
    def discard(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_deleted = True
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class ProposalStandardRequirementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProposalStandardRequirement.objects.all()
    serializer_class = ProposalStandardRequirementSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(text__icontains=search)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AmendmentRequestViewSet(viewsets.ModelViewSet):
    queryset = AmendmentRequest.objects.all()
    serializer_class = AmendmentRequestSerializer

    def create(self, request, *args, **kwargs):
        try:
            # reason_id=request.data.get('reason')
            # data = {
            #     #'schema': qs_proposal_type.order_by('-version').first().schema,
            #     'text': request.data.get('text'),
            #     'proposal': request.data.get('proposal'),
            #     'reason': AmendmentReason.objects.get(id=reason_id) if reason_id else None,
            # }
            #serializer = self.get_serializer(data= request.data)
            serializer = self.get_serializer(data= json.loads(request.data.get('data')))
            #serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception = True)
            instance = serializer.save()
            instance.add_documents(request)
            instance.generate_amendment(request)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['POST',])
    @renderer_classes((JSONRenderer,))
    def delete_document(self, request, *args, **kwargs):
        try:
            #import ipdb; ipdb.set_trace()
            instance = self.get_object()
            AmendmentRequestDocument.objects.get(id=request.data.get('id')).delete()
            return Response([dict(id=i.id, name=i.name,_file=i._file.url) for i in instance.requirement_documents.all()])
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(repr(e.error_dict))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class AmendmentRequestReasonChoicesView(views.APIView):

    renderer_classes = [JSONRenderer,]
    def get(self,request, format=None):
        choices_list = []
        #choices = AmendmentRequest.REASON_CHOICES
        choices=AmendmentReason.objects.all()
        if choices:
            for c in choices:
                #choices_list.append({'key': c[0],'value': c[1]})
                choices_list.append({'key': c.id,'value': c.reason})
        return Response(choices_list)


class SearchKeywordsView(views.APIView):
    renderer_classes = [JSONRenderer,]
    def post(self,request, format=None):
        qs = []
        searchWords = request.data.get('searchKeywords')
        searchProposal = request.data.get('searchProposal')
        searchApproval = request.data.get('searchApproval')
        searchCompliance = request.data.get('searchCompliance')
        if searchWords:
            qs= searchKeyWords(searchWords, searchProposal, searchApproval, searchCompliance)
        #queryset = list(set(qs))
        serializer = SearchKeywordSerializer(qs, many=True)
        return Response(serializer.data)


class SearchReferenceView(views.APIView):
    renderer_classes = [JSONRenderer,]
    def post(self,request, format=None):
        try:
            qs = []
            reference_number = request.data.get('reference_number')
            if reference_number:
                qs= search_reference(reference_number)
            #queryset = list(set(qs))
            serializer = SearchReferenceSerializer(qs)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except ValidationError as e:
            if hasattr(e,'error_dict'):
                raise serializers.ValidationError(repr(e.error_dict))
            else:
                print e
                raise serializers.ValidationError(repr(e[0].encode('utf-8')))
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class ApiaryReferralGroupViewSet(viewsets.ModelViewSet):
    queryset = ApiaryReferralGroup.objects.none()
    serializer_class = ApiaryReferralGroupSerializer

    def get_queryset(self):
        #user = self.request.user
        #import ipdb; ipdb.set_trace()
        if is_internal(self.request): #user.is_authenticated():
            return ApiaryReferralGroup.objects.all()
        else:
            return ApiaryReferralGroup.objects.none()

