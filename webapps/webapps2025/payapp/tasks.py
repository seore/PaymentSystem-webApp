from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def send_transaction_email(self, *, to_email, subject, template, context):
    html_body = render_to_string(template, context)
    text_body = render_to_string("emails/transaction.txt", context)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@payapp"),
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
