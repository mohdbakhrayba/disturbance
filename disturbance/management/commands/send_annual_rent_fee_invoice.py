from django.core.management.base import BaseCommand
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send annual rent fee invoices for the apiary'

    def handle(self, *args, **options):
        try:
            # TODO: Send annual rent fee once a year

            # 1. pick up the apiary licences (id=323 for develop)
            # 2. Create invoice
            # Rent fee can be retrieved from the ApiaryAnnualRentFee class
            # Run date can be retrieved from the ApiaryAnnualRentFeeRunDate class
            # TODO: Create invoices where payments is 0, therefore outstnding is equal to the annual rent fee
            # TODO: Attach the invoice and send emails
            pass

        except Exception as e:
            logger.error('Error command {}'.format(__name__))
