from django.core import mail
from django.conf import settings as django_settings
from django.test import TestCase
from django_mailer import engine, settings, send_mail, send_html_mail
from django_mailer.engine import send_queued_message
from django_mailer.models import QueuedMessage, Blacklist
from django_mailer.lockfile import FileLock

from StringIO import StringIO
import logging
import time


class LockTest(TestCase):
    """
    Tests for Django Mailer trying to send mail when the lock is already in
    place.
    """

    def setUp(self):
        # Create somewhere to store the log debug output. 
        self.output = StringIO()
        # Create a log handler which can capture the log debug output.
        self.handler = logging.StreamHandler(self.output)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        # Add the log handler.
        logger = logging.getLogger('django_mailer')
        logger.addHandler(self.handler)
        
        # Set the LOCK_WAIT_TIMEOUT to the default value.
        self.original_timeout = settings.LOCK_WAIT_TIMEOUT
        settings.LOCK_WAIT_TIMEOUT = 0

        # Use a test lock-file name in case something goes wrong, then emulate
        # that the lock file has already been acquired by another process.
        self.original_lock_path = engine.LOCK_PATH
        engine.LOCK_PATH += '.mailer-test'
        self.lock = FileLock(engine.LOCK_PATH)
        self.lock.unique_name += '.mailer_test'
        self.lock.acquire(0)

    def tearDown(self):
        # Remove the log handler.
        logger = logging.getLogger('django_mailer')
        logger.removeHandler(self.handler)

        # Revert the LOCK_WAIT_TIMEOUT to it's original value.
        settings.LOCK_WAIT_TIMEOUT = self.original_timeout

        # Revert the lock file unique name
        engine.LOCK_PATH = self.original_lock_path
        self.lock.release()

    def test_locked(self):
        # Acquire the lock so that send_all will fail.
        engine.send_all()
        self.output.seek(0)
        self.assertEqual(self.output.readlines()[-1].strip(),
                         'Lock already in place. Exiting.')
        # Try with a timeout.
        settings.LOCK_WAIT_TIMEOUT = .1
        engine.send_all()
        self.output.seek(0)
        self.assertEqual(self.output.readlines()[-1].strip(),
                         'Waiting for the lock timed out. Exiting.')

    def test_locked_timeoutbug(self):
        # We want to emulate the lock acquiring taking no time, so the next
        # three calls to time.time() always return 0 (then set it back to the
        # real function).
        original_time = time.time
        global time_call_count
        time_call_count = 0
        def fake_time():
            global time_call_count
            time_call_count = time_call_count + 1
            if time_call_count >= 3:
                time.time = original_time
            return 0
        time.time = fake_time
        try:
            engine.send_all()
            self.output.seek(0)
            self.assertEqual(self.output.readlines()[-1].strip(),
                             'Lock already in place. Exiting.')
        finally:
            time.time = original_time


class EngineTest(TestCase):
    
    
    def setUp(self):
        self.old_backend = django_settings.EMAIL_BACKEND
        django_settings.EMAIL_BACKEND = \
            'django.core.mail.backends.locmem.EmailBackend'
        from django.core import mail
        self.mail = mail
        self.connection = self.mail.get_connection()
    
    def tearDown(self):
        super(EngineTest, self).tearDown()
        django_settings.EMAIL_BACKEND = self.old_backend
    
    def test_send_queued_message(self):
        """
        Ensure that send_queued_message properly delivers email, regardless
        of whether connection is passed in.
        """
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message, self.connection)
        self.assertEqual(len(self.mail.outbox), 1)
        
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message)
        self.assertEqual(len(self.mail.outbox), 2)
        
        send_html_mail('Subject', 'Body', '<p>HTML</p>', 'from@example.com',
                       ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message, self.connection)
        self.assertEqual(len(self.mail.outbox), 3)
        
        send_html_mail('Subject', 'Body', '<p>HTML</p>', 'from@example.com',
                       ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message)
        self.assertEqual(len(self.mail.outbox), 4)

    
    def test_blacklist(self):
        """
        Test that blacklist works properly
        """
        Blacklist.objects.create(email='foo@bar.com')
        send_mail('Subject', 'Body', 'from@example.com', ['foo@bar.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message)
        self.assertEqual(len(self.mail.outbox), 0)
        
        # Explicitly passing in list of blacklisted addresses should also work
        send_mail('Subject', 'Body', 'from@example.com', ['bar@foo.com'])
        queued_message = QueuedMessage.objects.latest('id')
        send_queued_message(queued_message, blacklist=['bar@foo.com'])
        self.assertEqual(len(self.mail.outbox), 0)


    def test_sending_email_uses_opened_connection(self):
        """
        Test that send_queued_message command uses the connection that gets
        passed in as an argument. Connection stored in self is an instance of 
        locmem email backend. If we override the email backend with a dummy backend
        but passed in the previously opened connection from locmem backend, 
        we should still get the proper result since send_queued_message uses
        the connection we passed in.
        """
        django_settings.EMAIL_BACKEND = \
            'django.core.mail.backends.dummy.EmailBackend'
        # Outbox should be empty because send_queued_message uses dummy backend
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        engine.send_queued_message(queued_message)
        self.assertEqual(len(self.mail.outbox), 0)

        # Outbox should be populated because send_queued_message uses
        # the connection we passed in (locmem)
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        engine.send_queued_message(queued_message, self.connection)
        self.assertEqual(len(self.mail.outbox), 1)        


class ErrorHandlingTest(TestCase):

    def setUp(self):
        self.old_backend = django_settings.EMAIL_BACKEND
        django_settings.EMAIL_BACKEND = \
            'django_mailer.tests.base.RecipientErrorBackend'

    def tearDown(self):
        super(ErrorHandlingTest, self).tearDown()
        django_settings.EMAIL_BACKEND = self.old_backend    

    def test_queue_not_deleted_on_error(self):            
        """
        Queued message instance shouldn't be deleted when error is raised
        during sending
        """
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        engine.send_queued_message(queued_message)
        self.assertEqual(QueuedMessage.objects.count(), 1)
    
    def test_message_deferred(self):            
        """
        When error returned requires manual intervention to fix, 
        emails should be deferred.
        """
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        self.assertEqual(queued_message.deferred, None)
        engine.send_queued_message(queued_message)
        queued_message = QueuedMessage.objects.latest('id')
        self.assertNotEqual(queued_message.deferred, None)
        
        # If we see some other random errors email shouldn't be deferred
        django_settings.EMAIL_BACKEND = \
            'django_mailer.tests.base.OtherErrorBackend'
        send_mail('Subject', 'Body', 'from@example.com', ['to1@example.com'])
        queued_message = QueuedMessage.objects.latest('id')
        engine.send_queued_message(queued_message)
        self.assertEqual(queued_message.deferred, None)
    
