import datetime
import logging
from optparse import make_option

from django.core.management.base import BaseCommand

from django_mailer.management.commands import create_handler
from django_mailer.models import Message


class Command(BaseCommand):
    help = 'Place deferred messages back in the queue.'
    option_list = BaseCommand.option_list + (
        make_option('-d', '--days', type='int', default=90,
            help="Cleanup mails older than this many days, defaults to 90."),
    )

    def handle(self, verbosity, days, **options):
        # Delete mails and their related logs and queued created before X days
        logger = logging.getLogger('django_mailer')
        handler = create_handler(verbosity)
        logger.addHandler(handler)

        today = datetime.date.today()
        cutoff_date = today - datetime.timedelta(days)
        count = Message.objects.filter(date_created__lt=cutoff_date).count()
        Message.objects.filter(date_created__lt=cutoff_date).delete()
        logger.warning("Deleted %s mails created before %s " %
                       (count, cutoff_date))
