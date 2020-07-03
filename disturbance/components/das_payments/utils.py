import pytz
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from datetime import datetime, timedelta, date
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from ledger.accounts.models import EmailUser
from ledger.settings_base import TIME_ZONE

from disturbance.components.main.models import ApplicationType
from disturbance.components.proposals.models import Proposal, ProposalUserAction, SiteCategory, ApiarySiteFeeType, \
    ApiarySiteFeeRemainder
from disturbance.components.organisations.models import Organisation
from disturbance.components.das_payments.models import ApplicationFee, AnnualRentalFee, AnnualRentalFeeInvoice
from ledger.checkout.utils import create_basket_session, create_checkout_session, calculate_excl_gst
from ledger.payments.models import Invoice
from ledger.payments.utils import oracle_parser
import json
import ast
from decimal import Decimal

import logging

from disturbance.settings import PAYMENT_SYSTEM_ID

logger = logging.getLogger('payment_checkout')

def get_session_application_invoice(session):
    """ Application Fee session ID """
    if 'das_app_invoice' in session:
        application_fee_id = session['das_app_invoice']
    else:
        raise Exception('Application not in Session')

    try:
        #return Invoice.objects.get(id=application_invoice_id)
        #return Proposal.objects.get(id=proposal_id)
        return ApplicationFee.objects.get(id=application_fee_id)
    except Invoice.DoesNotExist:
        raise Exception('Application not found for application {}'.format(application_fee_id))


def set_session_application_invoice(session, application_fee):
    """ Application Fee session ID """
    session['das_app_invoice'] = application_fee.id
    session.modified = True


def delete_session_application_invoice(session):
    """ Application Fee session ID """
    if 'das_app_invoice' in session:
        del session['das_app_invoice']
        session.modified = True

def get_session_site_transfer_application_invoice(session):
    """ Application Fee session ID """
    if 'site_transfer_app_invoice' in session:
        application_fee_id = session['site_transfer_app_invoice']
    else:
        raise Exception('Application not in Session')

    try:
        #return Invoice.objects.get(id=application_invoice_id)
        #return Proposal.objects.get(id=proposal_id)
        return ApplicationFee.objects.get(id=application_fee_id)
    except Invoice.DoesNotExist:
        raise Exception('Application not found for application {}'.format(application_fee_id))


def set_session_site_transfer_application_invoice(session, application_fee):
    """ Application Fee session ID """
    session['site_transfer_app_invoice'] = application_fee.id
    session.modified = True


def delete_session_site_transfer_application_invoice(session):
    """ Application Fee session ID """
    if 'site_transfer_app_invoice' in session:
        del session['site_transfer_app_invoice']
        session.modified = True

def create_fee_lines_apiary(proposal):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    today_local = datetime.now(pytz.timezone(TIME_ZONE)).date()
    MIN_NUMBER_OF_SITES_TO_APPLY = 5
    line_items = []

    # applicant = EmailUser.objects.get(email='katsufumi.shibata@dbca.wa.gov.au')  # TODO: Get proper applicant

    # Calculate total number of sites applied per category
    summary = {}
    for apiary_site in proposal.proposal_apiary.apiary_sites.all():
        if apiary_site.site_category.id in summary:
            summary[apiary_site.site_category.id] += 1
        else:
            summary[apiary_site.site_category.id] = 1

    # Once payment success, data is updated based on this variable
    # This variable is stored in the session
    db_process_after_success = {'site_remainder_used': [], 'site_remainder_to_be_added': []}

    # Calculate number of sites to calculate the fee
    for site_category_id, number_of_sites_applied in summary.items():

        site_category = SiteCategory.objects.get(id=site_category_id)


        # Retrieve sites left
        filter_site_category = Q(site_category=site_category)
        filter_site_fee_type = Q(apiary_site_fee_type=ApiarySiteFeeType.objects.get(name=ApiarySiteFeeType.FEE_TYPE_APPLICATION))
        filter_applicant = Q(applicant=proposal.applicant)
        filter_proxy_applicant = Q(proxy_applicant=proposal.proxy_applicant)
        filter_expiry = Q(date_expiry__gte=today_local)
        filter_used = Q(date_used__isnull=True)
        site_fee_remainders = ApiarySiteFeeRemainder.objects.filter(
            filter_site_category &
            filter_site_fee_type &
            filter_applicant &
            filter_proxy_applicant &
            filter_expiry &
            filter_used
        ).order_by('date_expiry')  # Older comes earlier

        # Calculate deduction and set date_used field
        number_of_sites_after_deduction = number_of_sites_applied
        for site_left in site_fee_remainders:
            if number_of_sites_after_deduction == 0:
                break
            number_of_sites_after_deduction -= 1
            site_remainder_used = {
                'id': site_left.id,
                'date_used': today_local.strftime('%Y-%m-%d')
            }
            db_process_after_success['site_remainder_used'].append(site_remainder_used)

        quotient, remainder = divmod(number_of_sites_after_deduction, MIN_NUMBER_OF_SITES_TO_APPLY)
        number_of_sites_calculate = quotient * MIN_NUMBER_OF_SITES_TO_APPLY + MIN_NUMBER_OF_SITES_TO_APPLY if remainder else quotient * MIN_NUMBER_OF_SITES_TO_APPLY
        number_of_sites_to_add_as_remainder = number_of_sites_calculate - number_of_sites_after_deduction
        application_price = site_category.retrieve_current_fee_per_site_by_type(ApiarySiteFeeType.FEE_TYPE_APPLICATION)

        # Avoid ledger error
        # ledger doesn't accept quantity=0). Alternatively, set quantity=1 and price=0
        if number_of_sites_calculate == 0:
            number_of_sites_calculate = 1
            application_price = 0

        line_item = {
            'ledger_description': 'Application Fee - {} - {} - {}'.format(now, proposal.lodgement_number, site_category.name),
            'oracle_code': proposal.application_type.oracle_code_application,
            'price_incl_tax': application_price,
            'price_excl_tax': application_price if proposal.application_type.is_gst_exempt else calculate_excl_gst(application_price),
            'quantity': number_of_sites_calculate,
        }
        line_items.append(line_item)

        # Add remainders
        for i in range(number_of_sites_to_add_as_remainder):
            site_to_be_added = {
                'site_category_id': site_category.id,
                'apiary_site_fee_type_name': ApiarySiteFeeType.FEE_TYPE_APPLICATION,
                'applicant_id': proposal.applicant.id if proposal.applicant else None,
                'proxy_applicant_id': proposal.proxy_applicant.id if proposal.proxy_applicant else None,
                'date_expiry': (today_local + timedelta(days=7)).strftime('%Y-%m-%d')
            }
            db_process_after_success['site_remainder_to_be_added'].append(site_to_be_added)

    return line_items, db_process_after_success


def create_fee_lines(proposal, invoice_text=None, vouchers=[], internal=False):
    """ Create the ledger lines - line item for application fee sent to payment system """

    db_processes_after_success = {}

    if proposal.application_type.name == ApplicationType.APIARY:
        line_items, db_processes_after_success = create_fee_lines_apiary(proposal)  # This function returns line items and db_processes as a tuple
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Non 'Apiary' proposal
        application_price = proposal.application_type.application_fee
        line_items = [
            {
                'ledger_description': 'Application Fee - {} - {}'.format(now, proposal.lodgement_number),
                'oracle_code': proposal.application_type.oracle_code_application,
                'price_incl_tax':  application_price,
                'price_excl_tax':  application_price if proposal.application_type.is_gst_exempt else calculate_excl_gst(application_price),
                'quantity': 1,
            },
        ]

    logger.info('{}'.format(line_items))

    return line_items, db_processes_after_success


def checkout(request, proposal, lines, return_url_ns='public_payment_success', return_preload_url_ns='public_payment_success', invoice_text=None, vouchers=[], proxy=False):
    basket_params = {
        'products': lines,
        'vouchers': vouchers,
        'system': settings.PAYMENT_SYSTEM_ID,
        'custom_basket': True,
    }

    basket, basket_hash = create_basket_session(request, basket_params)
    #fallback_url = request.build_absolute_uri('/')
    checkout_params = {
        'system': settings.PAYMENT_SYSTEM_ID,
        'fallback_url': request.build_absolute_uri('/'),                                      # 'http://mooring-ria-jm.dbca.wa.gov.au/'
        'return_url': request.build_absolute_uri(reverse(return_url_ns)),          # 'http://mooring-ria-jm.dbca.wa.gov.au/success/'
        'return_preload_url': request.build_absolute_uri(reverse(return_url_ns)),  # 'http://mooring-ria-jm.dbca.wa.gov.au/success/'
        #'fallback_url': fallback_url,
        #'return_url': fallback_url,
        #'return_preload_url': fallback_url,
        'force_redirect': True,
        #'proxy': proxy,
        'invoice_text': invoice_text,                                                         # 'Reservation for Jawaid Mushtaq from 2019-05-17 to 2019-05-19 at RIA 005'
    }
#    if not internal:
#        checkout_params['check_url'] = request.build_absolute_uri('/api/booking/{}/booking_checkout_status.json'.format(booking.id))
    #if internal or request.user.is_anonymous():
    if proxy or request.user.is_anonymous():
        #checkout_params['basket_owner'] = booking.customer.id
        checkout_params['basket_owner'] = proposal.submitter_id


    create_checkout_session(request, checkout_params)

#    if internal:
#        response = place_order_submission(request)
#    else:
    response = HttpResponseRedirect(reverse('checkout:index'))
    # inject the current basket into the redirect response cookies
    # or else, anonymous users will be directionless
    response.set_cookie(
            settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
            max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
            secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
    )

#    if booking.cost_total < 0:
#        response = HttpResponseRedirect('/refund-payment')
#        response.set_cookie(
#            settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
#            max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
#            secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
#        )
#
#    # Zero booking costs
#    if booking.cost_total < 1 and booking.cost_total > -1:
#        response = HttpResponseRedirect('/no-payment')
#        response.set_cookie(
#            settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
#            max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
#            secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
#        )

    return response


def oracle_integration(date,override):
    system = '0517'
    oracle_codes = oracle_parser(date, system, 'Disturbance Approval System', override=override)


def create_other_invoice_for_annual_rental_fee(approval, request=None):
    """
    This function is called from the cron job to issue annual rental fee invoices
    """
    with transaction.atomic():
        try:
            logger.info('Creating OTHER invoice for the licence: {}'.format(approval.lodgement_number))
            order = create_invoice(approval, payment_method='other')
            invoice = Invoice.objects.get(order_number=order.number)

            # Create AnnualRentalFee object, which is linked from the approval
            # TODO: add 'calendar_year' field?
            # TODO: update 'cost' field?
            # TODO: add 'status' field or so?
            annual_rental_fee = AnnualRentalFee.objects.create(approval=approval)

            # Create AnnualRentalFeeInvoice object, which is linked form the annual_rental_fee object created above
            annual_rental_fee_invoice, created = AnnualRentalFeeInvoice.objects.get_or_create(
                annual_rental_fee=annual_rental_fee,
                invoice_reference=invoice.reference
            )

            return invoice

        except Exception, e:
            logger.error('Failed to create OTHER invoice for sanction outcome: {}'.format(approval))
            logger.error('{}'.format(e))


def create_invoice(approval, payment_method='bpay'):
    """
    This will create and invoice and order from a basket bypassing the session
    and payment bpoint code constraints.
    """
    from ledger.checkout.utils import createCustomBasket
    from ledger.payments.invoice.utils import CreateInvoiceBasket

    products = generate_line_items_for_annual_rental_fee(approval)
    user = approval.relevant_applicant
    invoice_text = 'Annual Rental Fee Invoice'

    basket = createCustomBasket(products, user, PAYMENT_SYSTEM_ID)
    order = CreateInvoiceBasket(
        payment_method=payment_method,
        system=PAYMENT_SYSTEM_ID
    ).create_invoice_and_order(basket, 0, None, None, user=user, invoice_text=invoice_text)

    return order


def calculate_total_annual_rental_fee():
    # TODO: implement
    #       Calendar year
    #       Rent fee can be retrieved from the ApiaryAnnualRentFee class
    #       Run date can be retrieved from the ApiaryAnnualRentFeeRunDate class
    return 123.45


def generate_line_items_for_annual_rental_fee(approval):
    """ Create the ledger lines - line item for the annual rental fee sent to payment system """

    now = datetime.now()
    now_date = now.date()

    penalty_amount = calculate_total_annual_rental_fee()

    line_items = [
        {'ledger_description': 'Annual Rental Fee: {}, Issued: {} {}'.format(
            approval.lodgement_number,
            now.strftime("%d/%m/%Y"),  # TODO: is now fine?
            now.strftime("%I:%M %p")), # TODO: is now fine?
            'oracle_code': 'ABC123 GST',
            'price_incl_tax': penalty_amount,
            'price_excl_tax': penalty_amount,
            'quantity': 1,
        },
    ]
    return line_items
