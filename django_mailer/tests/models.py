from django.core.mail import EmailMessage
from django.test import TestCase

from django_mailer.models import Message

class MailerModelTest(TestCase):
    
    def setUp(self):
        pass
        
    def test_email_message(self):
        """
        Test to make sure that Message model's "email_message" method
        returns a proper django EmailMessage instance
        """
        message = Message.objects.create(to_address='to@example.com',
            from_address='from@example.com', subject='Subject',
            message='Message')
        self.assertEqual(isinstance(message.email_message(), EmailMessage),
                         True)