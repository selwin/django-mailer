from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import models
from django_mailer import constants, managers
from django.utils.encoding import force_unicode

import datetime


PRIORITIES = (
    (constants.PRIORITY_HIGH, 'high'),
    (constants.PRIORITY_NORMAL, 'normal'),
    (constants.PRIORITY_LOW, 'low'),
)

RESULT_CODES = (
    (constants.RESULT_SENT, 'success'),
    (constants.RESULT_SKIPPED, 'not sent (blacklisted)'),
    (constants.RESULT_FAILED, 'failure'),
)


class Message(models.Model):
    """
    A model to hold email information.    
    """
    to_address = models.CharField(max_length=200)
    from_address = models.CharField(max_length=200)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    html_message = models.TextField(blank=True)
    date_created = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ('date_created',)

    def __unicode__(self):
        return '%s: %s' % (self.to_address, self.subject)

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object
        from a ``Message`` instance, depending on whether html_message is empty.
        """
        subject = force_unicode(self.subject)
        if self.html_message:
            msg = EmailMultiAlternatives(subject, self.message,
                                         self.from_address, [self.to_address],
                                         connection=connection)
            msg.attach_alternative(self.html_message, "text/html")
            return msg
        else:
            return EmailMessage(subject, self.message, self.from_address,
                                [self.to_address], connection=connection)


class QueuedMessage(models.Model):
    """
    A queued message.
    
    Messages in the queue can be prioritised so that the higher priority
    messages are sent first (secondarily sorted by the oldest message).
    
    """
    message = models.OneToOneField(Message, editable=False)
    priority = models.PositiveSmallIntegerField(choices=PRIORITIES,
                                            default=constants.PRIORITY_NORMAL)
    deferred = models.DateTimeField(null=True, blank=True)
    retries = models.PositiveIntegerField(default=0)
    date_queued = models.DateTimeField(default=datetime.datetime.now)

    objects = managers.QueueManager()

    class Meta:
        ordering = ('priority', 'date_queued')

    def defer(self):
        self.deferred = datetime.datetime.now()
        self.save()


class Blacklist(models.Model):
    """
    A blacklisted email address.
    
    Messages attempted to be sent to e-mail addresses which appear on this
    blacklist will be skipped entirely.
    
    """
    email = models.EmailField(max_length=200)
    date_added = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ('-date_added',)
        verbose_name = 'blacklisted e-mail address'
        verbose_name_plural = 'blacklisted e-mail addresses'


class Log(models.Model):
    """
    A log used to record the activity of a queued message.
    
    """
    message = models.ForeignKey(Message, editable=False)
    result = models.PositiveSmallIntegerField(choices=RESULT_CODES)
    date = models.DateTimeField(default=datetime.datetime.now)
    log_message = models.TextField()

    class Meta:
        ordering = ('-date',)
