import smtplib
from socket import error as SocketError

from django.conf import settings
from django.utils.importlib import import_module

from django_mailer import constants

# Provide a way of temporarily pausing the sending of mail.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)

if hasattr(settings, 'MAILER_USE_BACKEND'):
    MAILER_BACKEND = getattr(settings, 'MAILER_USE_BACKEND')
else:
    MAILER_BACKEND = getattr(settings, 'EMAIL_BACKEND')

# Default priorities for the mail_admins and mail_managers methods.
MAIL_ADMINS_PRIORITY = getattr(settings, 'MAILER_MAIL_ADMINS_PRIORITY',
                               constants.PRIORITY_HIGH)
MAIL_MANAGERS_PRIORITY = getattr(settings, 'MAILER_MAIL_MANAGERS_PRIORITY',
                                 None)

# When queue is empty, how long to wait (in seconds) before checking again.
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# Lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = max(getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", 0), 0)

# An optional alternate lock path, potentially useful if you have multiple
# projects running on the same server.
LOCK_PATH = getattr(settings, "MAILER_LOCK_PATH", None)

# Should be an interable containing dotted path to exceptions
# e.g: DEFER_ON_ERRORS = ('mail_backend.Exception1', 'mail_backend.Exception2')

error_paths = getattr(settings, 'MAILER_DEFER_ON_ERRORS', ())

if error_paths:
    errors = []
    for path in error_paths:
        try:
            mod_name, klass_name = path.rsplit('.', 1)
            mod = import_module(mod_name)
            try:
                klass = getattr(mod, klass_name)
            except AttributeError:
                raise ImproperlyConfigured(('Module "%s" does not define a '
                                            '"%s" class' % (mod_name, klass_name)))
            errors.append(klass)
        except ImportError, e:
            raise ImproperlyConfigured(('Error importing error class %s: "%s"'
                                % (mod_name, e)))
    DEFER_ON_ERRORS = tuple(errors)

else:
    # Default errors that cause mails to be deferred
    DEFER_ON_ERRORS = (SocketError, smtplib.SMTPSenderRefused,
        smtplib.SMTPRecipientsRefused, smtplib.SMTPAuthenticationError)
