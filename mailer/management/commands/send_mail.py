import logging
import signal

from django.conf import settings
from django.core.management.base import NoArgsCommand

from mailer.engine import send_all

#Limit script run time to 1 hour
def signal_handler(signum, frame):
    raise Exception("Timed out!")

signal.signal(signal.SIGALRM, signal_handler)
signal.alarm(3600)

# allow a sysadmin to pause the sending of mail temporarily.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)


class Command(NoArgsCommand):
    help = "Do one pass through the mail queue, attempting to send all mail."
    
    def handle_noargs(self, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        # if PAUSE_SEND is turned on don't do anything.
        if not PAUSE_SEND:
            send_all()
        else:
            logging.info("sending is paused, quitting.")
