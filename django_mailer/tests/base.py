from smtplib import SMTPRecipientsRefused

from django.core import mail
from django.test import TestCase
from django_mailer import queue_email_message
try:
    from django.core.mail import backends
    EMAIL_BACKEND_SUPPORT = True
except ImportError:
    # Django version < 1.2
    EMAIL_BACKEND_SUPPORT = False

class FakeConnection(object):
    """
    A fake SMTP connection which diverts emails to the test buffer rather than
    sending.
    
    """
    def sendmail(self, *args, **kwargs):
        """
        Divert an email to the test buffer.
        
        """
        #FUTURE: the EmailMessage attributes could be found by introspecting
        # the encoded message.
        message = mail.EmailMessage('SUBJECT', 'BODY', 'FROM', ['TO'])
        mail.outbox.append(message)


class RecipientErrorBackend(backends.base.BaseEmailBackend):
    '''
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    '''
    def send_messages(self, email_messages):
        raise SMTPRecipientsRefused('Fake Error')
        

class OtherErrorBackend(backends.base.BaseEmailBackend):
    '''
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    '''
    def send_messages(self, email_messages):
        raise Exception('Fake Error')


class MailerTestCase(TestCase):
    """
    A base class for Django Mailer test cases which diverts emails to the test
    buffer and provides some helper methods.
    
    """

    def queue_message(self, subject='test', message='a test message',
                      from_email='sender@djangomailer',
                      recipient_list=['recipient@djangomailer'],
                      priority=None):
        email_message = mail.EmailMessage(subject, message, from_email,
                                          recipient_list)
        return queue_email_message(email_message, priority=priority)