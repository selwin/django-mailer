"""Queued SMTP email backend class."""

from django.core.mail.backends.base import BaseEmailBackend

from django_mailer.constants import PRIORITIES, PRIORITY_EMAIL_NOW


class EmailBackend(BaseEmailBackend):
    '''
    A wrapper that manages a queued SMTP system.

    '''

    def send_messages(self, email_messages):
        """
        Add new messages to the email queue.

        The ``email_messages`` argument should be one or more instances
        of Django's core mail ``EmailMessage`` class.

        The messages can be assigned a priority in the queue by including
        an 'X-Mail-Queue-Priority' header set to one of the option strings
        in models.PRIORITIES.

        """
        if not email_messages:
            return

        from django_mailer import queue_email_message

        num_sent = 0
        
        '''
        Now that email sending actually calls backend's "send" method,
        this had to be tweaked to simply append to outbox when priority
        is "now". Passing email to queue_email_message with "now" priority
        will call this method again, causing infinite loop.
        '''
        for email_message in email_messages:
            priority = email_message.extra_headers.get('X-Mail-Queue-Priority',
                                                       None)
            if priority and PRIORITIES[priority] is PRIORITY_EMAIL_NOW:
                from django.core import mail
                mail.outbox.append(email_message)
            else:
                queue_email_message(email_message)
            num_sent += 1
        return num_sent
