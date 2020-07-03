from __future__ import unicode_literals

from datetime import datetime, timedelta
from django.db import models, transaction
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from ledger.accounts.models import EmailUser, RevisionedMixin
from ledger.payments.models import Invoice

from disturbance.components.approvals.models import Approval
from disturbance.components.proposals.models import Proposal
from decimal import Decimal as D
from ledger.checkout.utils import calculate_excl_gst

import logging
logger = logging.getLogger(__name__)


class Payment(RevisionedMixin):
    send_invoice = models.BooleanField(default=False)
    confirmation_sent = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    #expiry_time = models.DateTimeField(default=timezone.now() + timedelta(minutes=30), blank=True, null=True)
    expiry_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        app_label = 'disturbance'
        abstract = True

    @property
    def paid(self):
        payment_status = self.__check_payment_status()
        if payment_status == 'paid' or payment_status == 'over_paid':
            return True
        return False

    @property
    def unpaid(self):
        payment_status = self.__check_payment_status()
        if payment_status == 'unpaid':
            return True
        return False

    @property
    def amount_paid(self):
        return self.__check_payment_amount()

    def __check_payment_amount(self):
        amount = D('0.0')
        if self.active_invoice:
            return self.active_invoice.payment_amount
        return amount

    def __check_invoice_payment_status(self):
        invoices = []
        payment_amount = D('0.0')
        invoice_amount = D('0.0')
        references = self.invoices.all().values('invoice_reference')
        for r in references:
            try:
                invoices.append(Invoice.objects.get(reference=r.get("invoice_reference")))
            except Invoice.DoesNotExist:
                pass
        for i in invoices:
            if not i.voided:
                payment_amount += i.payment_amount
                invoice_amount += i.amount

        if invoice_amount == payment_amount:
            return 'paid'
        if payment_amount > invoice_amount:
            return 'over_paid'
        return "unpaid"

    def __check_payment_status(self):
        invoices = []
        amount = D('0.0')
        references = self.invoices.all().values('invoice_reference')
        for r in references:
            try:
                invoices.append(Invoice.objects.get(reference=r.get("invoice_reference")))
            except Invoice.DoesNotExist:
                pass
        for i in invoices:
            if not i.voided:
                amount += i.payment_amount

        if amount == 0:
            return 'unpaid'
        elif self.cost_total < amount:
            return 'over_paid'
        elif self.cost_total > amount:
            return 'partially_paid'
        return "paid"


class ApplicationFee(Payment):
    PAYMENT_TYPE_INTERNET = 0
    PAYMENT_TYPE_RECEPTION = 1
    PAYMENT_TYPE_BLACK = 2
    PAYMENT_TYPE_TEMPORARY = 3
    PAYMENT_TYPE_CHOICES = (
        (PAYMENT_TYPE_INTERNET, 'Internet booking'),
        (PAYMENT_TYPE_RECEPTION, 'Reception booking'),
        (PAYMENT_TYPE_BLACK, 'Black booking'),
        (PAYMENT_TYPE_TEMPORARY, 'Temporary reservation'),
    )

    proposal = models.ForeignKey(Proposal, on_delete=models.PROTECT, blank=True, null=True, related_name='application_fees')
    payment_type = models.SmallIntegerField(choices=PAYMENT_TYPE_CHOICES, default=0)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default='0.00')
    created_by = models.ForeignKey(EmailUser,on_delete=models.PROTECT, blank=True, null=True,related_name='created_by_application_fee')

    def __str__(self):
        return 'Application {} : Invoice {}'.format(self.proposal, self.application_fee_invoices.last())

    class Meta:
        app_label = 'disturbance'


class AnnualRentFee(Payment):
    PAYMENT_TYPE_INTERNET = 0
    PAYMENT_TYPE_RECEPTION = 1
    PAYMENT_TYPE_BLACK = 2
    PAYMENT_TYPE_TEMPORARY = 3
    PAYMENT_TYPE_CHOICES = (
        (PAYMENT_TYPE_INTERNET, 'Internet booking'),
        (PAYMENT_TYPE_RECEPTION, 'Reception booking'),
        (PAYMENT_TYPE_BLACK, 'Black booking'),
        (PAYMENT_TYPE_TEMPORARY, 'Temporary reservation'),
    )

    approval = models.ForeignKey(Approval, on_delete=models.PROTECT, blank=True, null=True, related_name='annual_rent_fees')
    payment_type = models.SmallIntegerField(choices=PAYMENT_TYPE_CHOICES, default=0)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default='0.00')
    created_by = models.ForeignKey(EmailUser, on_delete=models.PROTECT, blank=True, null=True, related_name='created_by_annual_rent_fee')

    def __str__(self):
        return 'Approval {} : Invoice {}'.format(self.approval, self.annual_rent_fee_invoices.last())

    class Meta:
        app_label = 'disturbance'


class ApplicationFeeInvoice(RevisionedMixin):
    application_fee = models.ForeignKey(ApplicationFee, related_name='application_fee_invoices')
    invoice_reference = models.CharField(max_length=50, null=True, blank=True, default='')

    def __str__(self):
        return 'Application Fee {} : Invoice #{}'.format(self.id,self.invoice_reference)

    class Meta:
        app_label = 'disturbance'

    @property
    def active(self):
        try:
            invoice = Invoice.objects.get(reference=self.invoice_reference)
            return False if invoice.voided else True
        except Invoice.DoesNotExist:
            pass
        return False


class AnnualRentFeeInvoice(RevisionedMixin):
    annual_rent_fee = models.ForeignKey(AnnualRentFee, related_name='annual_rent_fee_invoices')
    invoice_reference = models.CharField(max_length=50, null=True, blank=True, default='')

    def __str__(self):
        return 'Annual Rent Fee {} : Invoice #{}'.format(self.id, self.invoice_reference)

    class Meta:
        app_label = 'disturbance'

    @property
    def active(self):
        try:
            invoice = Invoice.objects.get(reference=self.invoice_reference)
            return False if invoice.voided else True
        except Invoice.DoesNotExist:
            pass
        return False


import reversion
reversion.register(ApplicationFee, follow=['application_fee_invoices'])
reversion.register(ApplicationFeeInvoice)
reversion.register(AnnualRentFee, follow=['annual_rent_fee_invoices'])
reversion.register(AnnualRentFeeInvoice)


