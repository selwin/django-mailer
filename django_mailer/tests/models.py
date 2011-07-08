from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import TestCase

from django_mailer import send_mail, send_html_mail
from django_mailer.models import Message

class MailerModelTest(TestCase):
    
    def setUp(self):
        pass
        
    def test_email_message(self):
        """
        Test to make sure that Message model's "email_message" method
        returns a proper django ``EmailMessage`` or `EmailMultiAlternatives``
        instance
        """
        msg = Message.objects.create(to_address='to@example.com',
            from_address='from@example.com', subject='Subject',
            message='Message')
        self.assertEqual(isinstance(msg.email_message(), EmailMessage), True)
                         
        msg = Message.objects.create(to_address='to@example.com',
            from_address='from@example.com', subject='Subject',
            message='Message', html_message='<p>HTML</p>')
        self.assertEqual(isinstance(msg.email_message(),EmailMultiAlternatives),
                         True)

    def test_send_mail(self):
        """
        Test to make sure that send_mail creates the right ``Message`` instance
        """
        subject = 'Subject'
        content = 'Body'
        from_address = 'from@example.com'
        to_addresses = ['to1@example.com', 'to2@example.com']
        send_mail(subject, content, from_address, to_addresses)
        message = Message.objects.get(pk=1)
        self.assertEqual(message.subject, subject)
        self.assertEqual(message.message, content)
        self.assertEqual(message.from_address, from_address)
        self.assertEqual(message.to_address, to_addresses[0])
        message = Message.objects.get(pk=2)
        self.assertEqual(message.subject, subject)
        self.assertEqual(message.message, content)
        self.assertEqual(message.from_address, from_address)
        self.assertEqual(message.to_address, to_addresses[1])
    
    def test_send_html_mail(self):
        """
        Test to make sure that send__html_mail creates the right ``Message``
        instance
        """
        subject = 'Subject'
        content = 'Body'
        html_content = '<p>Body</p>'
        from_address = 'from@example.com'
        to_address = ['to1@example.com']
        send_html_mail(subject, content, html_content, from_address, to_address)
        message = Message.objects.get(pk=1)
        self.assertEqual(message.subject, subject)
        self.assertEqual(message.message, content)
        self.assertEqual(message.html_message, html_content)
        self.assertEqual(message.from_address, from_address)
        self.assertEqual(message.to_address, to_address[0])
