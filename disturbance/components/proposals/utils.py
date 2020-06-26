import re

from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.geos import Point, GEOSGeometry
from preserialize.serialize import serialize
from ledger.accounts.models import EmailUser, Document
# <<<<<<< HEAD
from disturbance.components.proposals.models import ProposalDocument, ProposalUserAction, ApiarySite, SiteCategory, \
    ProposalApiaryTemporaryUse, TemporaryUseApiarySite, ApiaryApplicantChecklistAnswer
# ||||||| merged common ancestors
# from disturbance.components.proposals.models import ProposalDocument, ProposalUserAction, ApiarySite, SiteCategory
# =======
# from disturbance.components.proposals.models import ProposalDocument, ProposalUserAction, ApiarySite, SiteCategory, \
#     ApiaryApplicantChecklistAnswer
# >>>>>>> 1199cfade15f594dbeb87911b405a4cd30fa2307
from disturbance.components.proposals.serializers import SaveProposalSerializer

from disturbance.components.main.models import ApplicationType
from disturbance.components.proposals.models import (
    ProposalApiary,
    #ProposalApiaryTemporaryUse,
    #ProposalApiarySiteTransfer,
)
from disturbance.components.proposals.serializers_apiary import (
    ProposalApiarySerializer,
    ProposalApiaryTemporaryUseSerializer,
    ProposalApiarySiteTransferSerializer, ApiarySiteSerializer, TemporaryUseApiarySiteSerializer,
)
from disturbance.components.proposals.email import send_submit_email_notification, send_external_submit_email_notification

import traceback
import os
import json

import logging

from disturbance.utils import convert_moment_str_to_python_datetime_obj

logger = logging.getLogger(__name__)

def create_data_from_form(schema, post_data, file_data, post_data_index=None,special_fields=[],assessor_data=False):
    data = {}
    special_fields_list = []
    assessor_data_list = []
    comment_data_list = {}
    special_fields_search = SpecialFieldsSearch(special_fields)
    if assessor_data:
        assessor_fields_search = AssessorDataSearch()
        comment_fields_search = CommentDataSearch()
    try:
        for item in schema:
            data.update(_create_data_from_item(item, post_data, file_data, 0, ''))
            #_create_data_from_item(item, post_data, file_data, 0, '')
            special_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
            if assessor_data:
                assessor_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
                comment_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
        special_fields_list = special_fields_search.special_fields
        if assessor_data:
            assessor_data_list = assessor_fields_search.assessor_data
            comment_data_list = comment_fields_search.comment_data
    except:
        traceback.print_exc()
    if assessor_data:
        return [data],special_fields_list,assessor_data_list,comment_data_list

    return [data],special_fields_list


def _extend_item_name(name, suffix, repetition):
    return '{}{}-{}'.format(name, suffix, repetition)

def _create_data_from_item(item, post_data, file_data, repetition, suffix):
    item_data = {}

    if 'name' in item:
        extended_item_name = item['name']
    else:
        raise Exception('Missing name in item %s' % item['label'])

    #import ipdb; ipdb.set_trace()
    if 'children' not in item:
        if item['type'] in ['checkbox' 'declaration']:
            #item_data[item['name']] = post_data[item['name']]
            #import ipdb; ipdb.set_trace()
            item_data[item['name']] = extended_item_name in post_data
        elif item['type'] == 'file':
            if extended_item_name in file_data:
                item_data[item['name']] = str(file_data.get(extended_item_name))
                # TODO save the file here
            elif extended_item_name + '-existing' in post_data and len(post_data[extended_item_name + '-existing']) > 0:
                item_data[item['name']] = post_data.get(extended_item_name + '-existing')
            else:
                item_data[item['name']] = ''
        else:
            if extended_item_name in post_data:
                if item['type'] == 'multi-select':
                    item_data[item['name']] = post_data.getlist(extended_item_name)
                else:
                    item_data[item['name']] = post_data.get(extended_item_name)
    else:
        if 'repetition' in item:
            item_data = generate_item_data(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
        else:
            #import ipdb; ipdb.set_trace()
            item_data = generate_item_data(extended_item_name, item, item_data, post_data, file_data,1,suffix)


    if 'conditions' in item:
        for condition in item['conditions'].keys():
            for child in item['conditions'][condition]:
                item_data.update(_create_data_from_item(child, post_data, file_data, repetition, suffix))

    #import ipdb; ipdb.set_trace()
    return item_data

def generate_item_data(item_name,item,item_data,post_data,file_data,repetition,suffix):
    item_data_list = []
    for rep in xrange(0, repetition):
        #import ipdb; ipdb.set_trace()
        child_data = {}
        for child_item in item.get('children'):
            child_data.update(_create_data_from_item(child_item, post_data, file_data, 0,
                                                     '{}-{}'.format(suffix, rep)))
        item_data_list.append(child_data)

        item_data[item['name']] = item_data_list
    return item_data

class AssessorDataSearch(object):

    def __init__(self,lookup_field='canBeEditedByAssessor'):
        self.lookup_field = lookup_field
        self.assessor_data = []

    def extract_assessor_data(self,item,post_data):
        values = []
        res = {
            'name': item,
            'assessor': '',
            'referrals':[]
        }
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}-'.format(item))
                    if len(parts) > 1:
                        # split parts to see if referall
                        ref_parts = parts[1].split('Referral-')
                        if len(ref_parts) > 1:
                            # Referrals
                            res['referrals'].append({
                                'value':v,
                                'email':ref_parts[1],
                                'full_name': EmailUser.objects.get(email=ref_parts[1].lower()).get_full_name()
                            })
                        elif k.split('-')[-1].lower() == 'assessor':
                            # Assessor
                            res['assessor'] = v

        return res

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            if 'conditions' in item:
                for condition in item['conditions'].keys():
                    for child in item['conditions'][condition]:
                        item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

            if item.get(self.lookup_field):
                self.assessor_data.append(self.extract_assessor_data(extended_item_name,post_data))

        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)

            if 'conditions' in item:
                for condition in item['conditions'].keys():
                    for child in item['conditions'][condition]:
                        item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in xrange(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data

class CommentDataSearch(object):

    def __init__(self,lookup_field='canBeEditedByAssessor'):
        self.lookup_field = lookup_field
        self.comment_data = {}

    def extract_comment_data_original(self,item,post_data):
        res = {}
        values = []
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            #import ipdb; ipdb.set_trace()
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}'.format(item))
                    if len(parts) > 1:
                        ref_parts = parts[1].split('-comment-field')
                        if len(ref_parts) > 1:
                            if len(ref_parts)==2 and ref_parts[0]=='' and ref_parts[1]=='':
                                print(v)
                                #if('{}'.format(item)=="Section0-1"):
                                #print(item,v, parts, ref_parts)
                            res = {'{}'.format(item):v}
        return res

    def extract_comment_data(self,item,post_data):
        res = {}
        values = []
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            #import ipdb; ipdb.set_trace()
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}'.format(item))
                    if len(parts) > 1:
                        ref_parts = parts[1].split('-comment-field')
                        if len(ref_parts) > 1:
                            if len(ref_parts)==2 and ref_parts[0]=='' and ref_parts[1]=='':
                                res = {'{}'.format(item):v}
        return res

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            #print(item, extended_item_name)
            self.comment_data.update(self.extract_comment_data(extended_item_name,post_data))

        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)


        if 'conditions' in item:
            for condition in item['conditions'].keys():
                for child in item['conditions'][condition]:
                    item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in xrange(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data

class SpecialFieldsSearch(object):

    def __init__(self,lookable_fields):
        self.lookable_fields = lookable_fields
        self.special_fields = {}

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            for f in self.lookable_fields:
                if item['type'] in ['checkbox' 'declaration']:
                    val = None
                    val = item.get(f,None)
                    if val:
                        item_data[f] = extended_item_name in post_data
                        self.special_fields.update(item_data)
                else:
                    if extended_item_name in post_data:
                        val = None
                        val = item.get(f,None)
                        if val:
                            if item['type'] == 'multi-select':
                                item_data[f] = ','.join(post_data.getlist(extended_item_name))
                            else:
                                item_data[f] = post_data.get(extended_item_name)
                            self.special_fields.update(item_data)
        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)


        if 'conditions' in item:
            for condition in item['conditions'].keys():
                for child in item['conditions'][condition]:
                    item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in xrange(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data


# -------------------------------------------------------------------------------------------------------------
# APIARY Section starts here
# -------------------------------------------------------------------------------------------------------------

def save_proponent_data(instance, request, viewset):
    if instance.apiary_group_application_type:
        save_proponent_data_apiary(instance, request, viewset)
    else:
        save_proponent_data_disturbance(instance,request,viewset)


def save_proponent_data_apiary(proposal_obj, request, viewset):
    with transaction.atomic():
        #import ipdb; ipdb.set_trace()
        try:
            data = {
            }

            try:
                schema = request.data.get('schema')
            except:
                schema = request.POST.get('schema')

            sc = json.loads(schema) if schema else {}

            #save Site Locations data
            site_location_data = sc.get('proposal_apiary', None)

            if site_location_data:
                # New apairy site application
                serializer = ProposalApiarySerializer(proposal_obj.proposal_apiary, data=site_location_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                # site_locations_received = site_location_data['apiary_sites']
                site_locations_received = json.loads(request.data.get('all_the_features'))

                # Feature object doesn't have a field named 'id' originally unless manually added
                # The field 'id_' is used in the frontend, though
                site_ids_received = [feature['id'] if 'id' in feature else '' for feature in site_locations_received]  # if hasattr(feature, 'id')]
                site_ids_existing = [site.id for site in ApiarySite.objects.filter(proposal_apiary_id=site_location_data['id'])]
                site_ids_delete = [id for id in site_ids_existing if id not in site_ids_received]

                # Handle ApiarySites here
                for index, feature in enumerate(site_locations_received):
                    feature['proposal_apiary_id'] = proposal_obj.proposal_apiary.id

                    if viewset.action == 'submit':
                        # When this function is called for the 'submit', we want to the apiary_sites' status 'suspended'
                        feature['status'] = ApiarySite.STATUS_SUSPENDED

                    try:
                        # Update existing
                        a_site = ApiarySite.objects.get(site_guid=feature['id_'])
                        serializer = ApiarySiteSerializer(a_site, data=feature)
                    except ApiarySite.DoesNotExist:
                        # Create new
                        if feature['values_']['site_category'] == 'south_west':
                            category_obj = SiteCategory.objects.get(name='south_west')
                        else:
                            category_obj = SiteCategory.objects.get(name='remote')
                        feature['site_category_id'] = category_obj.id
                        feature['site_guid'] = feature['id_']

                        serializer = ApiarySiteSerializer(data=feature)

                    serializer.is_valid(raise_exception=True)
                    apiary_site_obj = serializer.save()

                    # Save coordinate
                    geom_str = GEOSGeometry(
                        'POINT(' +
                            str(feature['values_']['geometry']['flatCoordinates'][0]) + ' ' +
                            str(feature['values_']['geometry']['flatCoordinates'][1]) +
                        ')',
                        srid=4326
                    )
                    apiary_site_obj.wkb_geometry = geom_str
                    apiary_site_obj.save()
                # END: Handle ApiarySites

                for new_answer in site_location_data['checklist_answers']:
                    ans = ApiaryApplicantChecklistAnswer.objects.get(id=new_answer['id'])
                    ans.answer = new_answer['answer']
                    ans.save()

                # Delete existing
                sites_delete = ApiarySite.objects.filter(id__in=site_ids_delete)
                sites_delete.delete()

            #save Temporary Use data
            temporary_use_data = request.data.get('apiary_temporary_use', None)
            if temporary_use_data:
                # Temporary Use Application
                apiary_temporary_use_obj = ProposalApiaryTemporaryUse.objects.get(id=request.data.get('apiary_temporary_use')['id'])
                apiary_temporary_use_data = request.data.get('apiary_temporary_use')
                update_proposal_apiary_temporary_use(apiary_temporary_use_obj, apiary_temporary_use_data)

                if viewset.action == 'submit':
                    proposal_obj.processing_status = 'with_assessor'
                    proposal_obj.customer_status = 'with_assessor'
                    proposal_obj.documents.all().update(can_delete=False)
                    #proposal.required_documents.all().update(can_delete=False)
                    proposal_obj.save()

                # return redirect(reverse('external-proposal-temporary-use-submit-success', kwargs={'proposal_pk': proposal_obj.id}))

            #save Site Transfer data
            site_transfer_data = request.data.get('apiary_site_transfer', None)
            if site_transfer_data:
                serializer = ProposalApiarySiteTransferSerializer(proposal_obj.apiary_site_transfer, data=site_transfer_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            # save/update any additonal special propoerties here
            proposal_obj.title = proposal_obj.proposal_apiary.title if hasattr(proposal_obj, 'proposal_apiary') else proposal_obj.title
            proposal_obj.activity = proposal_obj.application_type.name
            proposal_obj.save()
        except Exception as e:
            raise


def update_proposal_apiary_temporary_use(temp_use_obj, temp_use_data):
    temp_use_data['from_date'] = convert_moment_str_to_python_datetime_obj(temp_use_data['from_date']).date() if temp_use_data['from_date'] else None
    temp_use_data['to_date'] = convert_moment_str_to_python_datetime_obj(temp_use_data['to_date']).date() if temp_use_data['to_date'] else None
    serializer = ProposalApiaryTemporaryUseSerializer(temp_use_obj, data=temp_use_data)
    serializer.is_valid(raise_exception=True)
    patu = serializer.save()

    # Update TemporaryUseApiarySite
    for item in temp_use_data['temporary_use_apiary_sites']:
        item['selected'] = item['apiary_site']['checked']
        tuas_obj = TemporaryUseApiarySite.objects.get(id=item['id'])

        serializer = TemporaryUseApiarySiteSerializer(tuas_obj, data=item)
        serializer.is_valid(raise_exception=True)
        serializer.save()


def save_proponent_data_disturbance(instance,request,viewset):
    with transaction.atomic():
        try:
            lookable_fields = ['isTitleColumnForDashboard','isActivityColumnForDashboard','isRegionColumnForDashboard']

            extracted_fields,special_fields = create_data_from_form(instance.schema, request.POST, request.FILES, special_fields=lookable_fields)
            instance.data = extracted_fields
            #import ipdb; ipdb.set_trace()

            form_data=json.loads(request.POST['schema'])
            sub_activity_level1=form_data.get('sub_activity_level1')
            print(sub_activity_level1)

            logger.info("Region: {}, Activity: {}".format(special_fields.get('isRegionColumnForDashboard',None), special_fields.get('isActivityColumnForDashboard',None)))

            data1 = {
                #'region': special_fields.get('isRegionColumnForDashboard',None),
                'title': special_fields.get('isTitleColumnForDashboard',None),
                'activity': special_fields.get('isActivityColumnForDashboard',None),

                'data': extracted_fields,
                'processing_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.processing_status,
                'customer_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.customer_status,
                # 'lodgement_sequence': 1 if instance.lodgement_sequence == 0 else instance.lodgement_sequence,

            }
            data = {
                #'region': special_fields.get('isRegionColumnForDashboard',None),
                'title': special_fields.get('isTitleColumnForDashboard',None),

                'data': extracted_fields,
                'processing_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.processing_status,
                'customer_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.customer_status,
                # 'lodgement_sequence': 1 if instance.lodgement_sequence == 0 else instance.lodgement_sequence,
                'activity': form_data.get('activity',None),
                'region': form_data.get('region',None),
                'district': form_data.get('district',None),
                'sub_activity_level1': form_data.get('sub_activity_level1',None),
                'sub_activity_level2': form_data.get('sub_activity_level2',None),
                'management_area': form_data.get('management_area',None),
                'approval_level': form_data.get('approval_level',None),

            }

            serializer = SaveProposalSerializer(instance, data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            instance.log_user_action(ProposalUserAction.ACTION_SAVE_APPLICATION.format(instance.id),request)

            # Save Documents
        #            for f in request.FILES:
        #                try:
        #                    #document = instance.documents.get(name=str(request.FILES[f]))
        #                    document = instance.documents.get(input_name=f)
        #                except ProposalDocument.DoesNotExist:
        #                    document = instance.documents.get_or_create(input_name=f)[0]
        #                document.name = str(request.FILES[f])
        #                if document._file and os.path.isfile(document._file.path):
        #                    os.remove(document._file.path)
        #                document._file = request.FILES[f]
        #                document.save()

        #            for f in request.FILES:
        #                #import ipdb; ipdb; ipdb.set_trace()
        #                try:
        #                   document = instance.documents.get(input_name=f, name=request.FILES[f].name)
        #                except ProposalDocument.DoesNotExist:
        #                   document = instance.documents.get_or_create(input_name=f, name=request.FILES[f].name)[0]
        #                document._file = request.FILES[f]
        #                document.save()

        # End Save Documents
        except:
            raise


def save_assessor_data(instance,request,viewset):
    with transaction.atomic():
        try:
            lookable_fields = ['isTitleColumnForDashboard','isActivityColumnForDashboard','isRegionColumnForDashboard']
            extracted_fields,special_fields,assessor_data,comment_data = create_data_from_form(
                instance.schema, request.POST, request.FILES,special_fields=lookable_fields,assessor_data=True)

            logger.info("ASSESSOR DATA - Region: {}, Activity: {}".format(special_fields.get('isRegionColumnForDashboard',None), special_fields.get('isActivityColumnForDashboard',None)))

            data = {
                'data': extracted_fields,
                'assessor_data': assessor_data,
                'comment_data': comment_data,
            }
            serializer = SaveProposalSerializer(instance, data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            # Save Documents
            for f in request.FILES:
                try:
                    #document = instance.documents.get(name=str(request.FILES[f]))
                    document = instance.documents.get(input_name=f)
                except ProposalDocument.DoesNotExist:
                    document = instance.documents.get_or_create(input_name=f)[0]
                document.name = str(request.FILES[f])
                if document._file and os.path.isfile(document._file.path):
                    os.remove(document._file.path)
                document._file = request.FILES[f]
                document.save()
            # End Save Documents
            instance.log_user_action(ProposalUserAction.ACTION_SAVE_APPLICATION.format(instance.id),request)
        except:
            raise


def save_apiary_assessor_data(instance,request,viewset):
    with transaction.atomic():
        try:
            #lookable_fields = ['isTitleColumnForDashboard','isActivityColumnForDashboard','isRegionColumnForDashboard']
            #extracted_fields,special_fields,assessor_data,comment_data = create_data_from_form(
             #   instance.schema, request.POST, request.FILES,special_fields=lookable_fields,assessor_data=True)

            #logger.info("ASSESSOR DATA - Region: {}, Activity: {}".format(special_fields.get('isRegionColumnForDashboard',None), special_fields.get('isActivityColumnForDashboard',None)))

            #data = {
               # 'data': extracted_fields,
              #  'assessor_data': assessor_data,
             #   'comment_data': comment_data,
            #}
            #serializer = SaveProposalSerializer(instance, data, partial=True)
            serializer = SaveProposalSerializer(instance, request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            # Save Documents
            for f in request.FILES:
                try:
                    #document = instance.documents.get(name=str(request.FILES[f]))
                    document = instance.documents.get(input_name=f)
                except ProposalDocument.DoesNotExist:
                    document = instance.documents.get_or_create(input_name=f)[0]
                document.name = str(request.FILES[f])
                if document._file and os.path.isfile(document._file.path):
                    os.remove(document._file.path)
                document._file = request.FILES[f]
                document.save()
            # End Save Documents
            instance.log_user_action(ProposalUserAction.APIARY_ACTION_SAVE_APPLICATION.format(instance.id),request)
        except:
            raise


def proposal_submit_apiary(proposal, request):
    with transaction.atomic():
        if proposal.can_user_edit:
            proposal.submitter = request.user
            #proposal.lodgement_date = datetime.datetime.strptime(timezone.now().strftime('%Y-%m-%d'),'%Y-%m-%d').date()
            proposal.lodgement_date = timezone.now()
            proposal.training_completed = True
            if (proposal.amendment_requests):
                qs = proposal.amendment_requests.filter(status = "requested")
                if (qs):
                    for q in qs:
                        q.status = 'amended'
                        q.save()

            # Create a log entry for the proposal
            proposal.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.id),request)
            # Create a log entry for the organisation
            #proposal.applicant.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.id),request)
            applicant_field=getattr(proposal, proposal.applicant_field)
            applicant_field.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.id),request)

            ret1 = send_submit_email_notification(request, proposal)
            ret2 = send_external_submit_email_notification(request, proposal)

            #proposal.save_form_tabs(request)
            if ret1 and ret2:
                proposal.processing_status = 'with_assessor'
                proposal.customer_status = 'with_assessor'
                proposal.documents.all().update(can_delete=False)
                #proposal.required_documents.all().update(can_delete=False)
                proposal.save()
            else:
                raise ValidationError('An error occurred while submitting proposal (Submit email notifications failed)')
            #Create assessor checklist with the current assessor_list type questions
            #Assessment instance already exits then skip.
#            try:
#                assessor_assessment=ProposalAssessment.objects.get(proposal=proposal,referral_group=None, referral_assessment=False)
#            except ProposalAssessment.DoesNotExist:
#                assessor_assessment=ProposalAssessment.objects.create(proposal=proposal,referral_group=None, referral_assessment=False)
#                checklist=ChecklistQuestion.objects.filter(list_type='assessor_list', obsolete=False)
#                for chk in checklist:
#                    try:
#                        chk_instance=ProposalAssessmentAnswer.objects.get(question=chk, assessment=assessor_assessment)
#                    except ProposalAssessmentAnswer.DoesNotExist:
#                        chk_instance=ProposalAssessmentAnswer.objects.create(question=chk, assessment=assessor_assessment)
#
            return proposal

        else:
            raise ValidationError('You can\'t edit this proposal at this moment')


def clone_proposal_with_status_reset(proposal):
    with transaction.atomic():
        try:
            proposal.customer_status = 'draft'
            proposal.processing_status = 'draft'
            proposal.assessor_data = {}
            proposal.comment_data = {}

            #proposal.id_check_status = 'not_checked'
            #proposal.character_check_status = 'not_checked'
            #proposal.compliance_check_status = 'not_checked'
            #Sproposal.review_status = 'not_reviewed'

            proposal.lodgement_number = ''
            proposal.lodgement_sequence = 0
            proposal.lodgement_date = None

            proposal.assigned_officer = None
            proposal.assigned_approver = None

            proposal.approval = None

            original_proposal_id = proposal.id

            proposal.previous_proposal = proposal.objects.get(id=original_proposal_id)

            proposal.id = None

            #proposal.save(no_revision=True)
            proposal.save()


            # clone documents
            for proposal_document in ProposalDocument.objects.filter(proposal=original_proposal_id):
                proposal_document.proposal = proposal
                proposal_document.id = None
                proposal_document.save()

            return proposal
        except:
            raise

