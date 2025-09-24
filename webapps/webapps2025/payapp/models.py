from decimal import Decimal
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import MinValueValidator
from payapp.constants import CURRENCY_CHOICES, STATUS_CHOICES


class CustomUser(AbstractUser):
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GBP')
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name='%(app_label)s_%(class)s_groups',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='%(app_label)s_%(class)s_permissions',
        related_query_name='user',
    )

    def __str__(self):
        return self.username


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(750.00), validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.user.username}'s Account"


class Transaction(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_transactions', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    converted_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    converted_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True)
    conversion_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['sender']),
            models.Index(fields=['recipient'])
        ]

    def __str__(self):
        return f"{self.sender.username} →  {self.recipient.username}: {self.amount} {self.sender.currency} ({self.status})"
