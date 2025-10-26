# shop/signals.py
"""from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order

@receiver(post_save, sender=Order)
def order_created_send_email(sender, instance, created, **kwargs):
    if created:
        subject = f"New Order #{instance.id} by {instance.user.username}"
        message = f"User: {instance.user.username}\nEmail: {instance.user.email}\nTotal: {instance.total_amount}\nOrder ID: {instance.id}"
        recipient_list = [settings.EMAIL_HOST_USER]  # or admin emails list
        send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)
"""