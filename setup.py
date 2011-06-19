from distutils.core import setup
from django_mailer import get_version


setup(
    name='django-mailer-2',
    version=get_version(),
    description=("A reusable Django app for queueing the sending of email "
                 "(forked from James Tauber's django-mailer)"),
    long_description=open('docs/usage.txt').read(),
    author='Chris Beaven',
    author_email='smileychris@gmail.com',
    url='http://github.com/SmileyChris/django-mailer-2',
    packages=[
        'django_mailer',
        'django_mailer.management',
        'django_mailer.management.commands',
        'django_mailer.tests',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
