"""
The "engine room" of django mailer.

Methods here actually handle the sending of queued messages.

"""

from django_mailer import constants, models, settings
from lockfile import FileLock, AlreadyLocked, LockTimeout
from socket import error as SocketError
import logging
import os
import smtplib
import tempfile
import time

if constants.EMAIL_BACKEND_SUPPORT:
    from django.core.mail import get_connection
else:
    from django.core.mail import SMTPConnection as get_connection

LOCK_PATH = settings.LOCK_PATH or os.path.join(tempfile.gettempdir(),
                                               'send_mail')

logger = logging.getLogger('django_mailer.engine')


def _message_queue(block_size, exclude_messages=[]):
    """
    A generator which iterates queued messages in blocks so that new
    prioritised messages can be inserted during iteration of a large number of
    queued messages.

    To avoid an infinite loop, yielded messages *must* be deleted or deferred.

    """
    def get_block():
        queue = models.QueuedMessage.objects.non_deferred() \
            .exclude(pk__in=exclude_messages).select_related()
        if block_size:
            queue = queue[:block_size]
        return queue
    queue = get_block()
    while queue:
        for message in queue:
            yield message
        queue = get_block()


def send_all(block_size=500, backend=None):
    """
    Send all non-deferred messages in the queue.

    A lock file is used to ensure that this process can not be started again
    while it is already running.

    The ``block_size`` argument allows for queued messages to be iterated in
    blocks, allowing new prioritised messages to be inserted during iteration
    of a large number of queued messages.

    """
    lock = FileLock(LOCK_PATH)

    logger.debug("Acquiring lock...")
    try:
        # lockfile has a bug dealing with a negative LOCK_WAIT_TIMEOUT (which
        # is the default if it's not provided) systems which use a LinkFileLock
        # so ensure that it is never a negative number.
        lock.acquire(settings.LOCK_WAIT_TIMEOUT or 0)
        #lock.acquire(settings.LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logger.debug("Lock already in place. Exiting.")
        return
    except LockTimeout:
        logger.debug("Waiting for the lock timed out. Exiting.")
        return
    logger.debug("Lock acquired.")

    start_time = time.time()

    sent = deferred = skipped = 0

    # A list of messages to be sent, usually contains messages that failed
    exclude_messages = []

    try:
        if constants.EMAIL_BACKEND_SUPPORT:
            connection = get_connection(backend=backend)
        else:
            connection = get_connection()
        blacklist = models.Blacklist.objects.values_list('email', flat=True)
        connection.open()
        for message in _message_queue(block_size, exclude_messages=exclude_messages):
            result = send_queued_message(message, connection=connection,
                                  blacklist=blacklist)
            if result == constants.RESULT_SENT:
                sent += 1
            elif result == constants.RESULT_FAILED:
                deferred += 1
                # Don't try to send this message again for now
                exclude_messages.append(message.pk)
            elif result == constants.RESULT_SKIPPED:
                skipped += 1
        connection.close()
    finally:
        logger.debug("Releasing lock...")
        lock.release()
        logger.debug("Lock released.")

    logger.debug("")
    if sent or deferred or skipped:
        log = logger.warning
    else:
        log = logger.info
    log("%s sent, %s deferred, %s skipped." % (sent, deferred, skipped))
    logger.debug("Completed in %.2f seconds." % (time.time() - start_time))


def send_loop(empty_queue_sleep=None):
    """
    Loop indefinitely, checking queue at intervals and sending and queued
    messages.

    The interval (in seconds) can be provided as the ``empty_queue_sleep``
    argument. The default is attempted to be retrieved from the
    ``MAILER_EMPTY_QUEUE_SLEEP`` setting (or if not set, 30s is used).

    """
    empty_queue_sleep = empty_queue_sleep or settings.EMPTY_QUEUE_SLEEP
    while True:
        while not models.QueuedMessage.objects.all():
            logger.debug("Sleeping for %s seconds before checking queue "
                          "again." % empty_queue_sleep)
            time.sleep(empty_queue_sleep)
        send_all()


def send_queued_message(queued_message, connection=None, blacklist=None,
                 log=True):
    """
    Send a queued message, returning a response code as to the action taken.

    The response codes can be found in ``django_mailer.constants``. The
    response will be either ``RESULT_SKIPPED`` for a blacklisted email,
    ``RESULT_FAILED`` for a deferred message or ``RESULT_SENT`` for a
    successful sent message.

    To allow optimizations if multiple messages are to be sent, a
    connection can be provided and a list of blacklisted email addresses.
    Otherwise a new connection will be opened to send this message and the
    email recipient address checked against the ``Blacklist`` table.

    If the message recipient is blacklisted, the message will be removed from
    the queue without being sent. Otherwise, the message is attempted to be
    sent with an SMTP failure resulting in the message being flagged as
    deferred so it can be tried again later.

    By default, a log is created as to the action. Either way, the original
    message is not deleted.

    """
    message = queued_message.message
    if connection is None:
        connection = get_connection()
        connection.open()
        arg_connection = False
    else:
        arg_connection = True

    if blacklist is None:
        blacklisted = models.Blacklist.objects.filter(email=message.to_address)
    else:
        blacklisted = message.to_address in blacklist

    if blacklisted:
        logger.info("Not sending to blacklisted email: %s" %
                     message.to_address.encode("utf-8"))
        queued_message.delete()
        result = constants.RESULT_SKIPPED
    else:
        result = send_message(message, connection=connection)

    if not arg_connection:
        connection.close()
    return result


def send_message(message, connection=None):
    """
    Send an EmailMessage, returning a response code as to the action taken.

    The response codes can be found in ``django_mailer.constants``. The
    response will be either ``RESULT_FAILED`` for a failed send or
    ``RESULT_SENT`` for a successfully sent message.

    To allow optimizations if multiple messages are to be sent, a
    connection can be provided. Otherwise a new connection will be opened
    to send this message.

    This function does not perform any logging or queueing.

    """
    if connection is None:
        connection = get_connection()
    opened_connection = False

    try:
        logger.info("Sending message to %s: %s" %
                     (message.to_address.encode("utf-8"),
                      message.subject.encode("utf-8")))
        message.email_message(connection=connection).send()
        message.queuedmessage.delete()
        result = constants.RESULT_SENT
        log_message = 'Sent'
    except Exception, err:
        if isinstance(err, settings.DEFER_ON_ERRORS):
            message.queuedmessage.defer()
        logger.warning("Message to %s deferred due to failure: %s" %
                        (message.to_address.encode("utf-8"), err))
        log_message = unicode(err)
        result = constants.RESULT_FAILED
    
    models.Log.objects.create(message=message, result=result,
                              log_message=log_message)

    if opened_connection:
        connection.close()
    return result
