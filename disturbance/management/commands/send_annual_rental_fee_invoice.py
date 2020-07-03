from django.core.management.base import BaseCommand
import logging
from django.db.models import Q, Min
from disturbance.components.approvals.models import Approval
from disturbance.components.das_payments.utils import create_other_invoice_for_annual_rental_fee


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send annual rent fee invoices for the apiary'

    def handle(self, *args, **options):
        try:
            # TODO: Develop query parameters to retrieve approvals
            #       invoice.payment_status not in ('paid', 'overpaid',)
            # Invoice.objects.exclude(payment_status__in=('paid', 'overpaid')

            q_objects = Q()
            q_objects &= Q(id=323)

            approval_qs = Approval.objects.filter(q_objects)

            for approval in approval_qs:
                invoice = create_other_invoice_for_annual_rental_fee(approval)

                # TODO: Attach the invoice and send emails


        except Exception as e:
            logger.error('Error command {}'.format(__name__))
