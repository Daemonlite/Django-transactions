from django.test import TestCase
from django.core.mail import send_mail
# Create your tests here.
subject = "Transaction Notification"
message = "You have received a notification from a your recent buyer."
from_email = "paakwesinunoo135@gmail.com"
recipient_list = 'khemikal2016@gmail.com'

send_mail(subject, message, from_email, recipient_list)