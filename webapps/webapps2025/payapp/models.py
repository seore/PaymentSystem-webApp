import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class PaymentRequest(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_requests",
    )
    short_code = models.CharField(max_length=12, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="GBP")
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.short_code} - {self.amount} {self.currency} ({self.status})"

    def is_expired(self) -> bool:
        return self.expires_at and timezone.now() > self.expires_at


class Transaction(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_REFUNDED = "REFUNDED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_request = models.ForeignKey(
        PaymentRequest,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="GBP")
    provider_txn_id = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.id} - {self.status} - {self.amount} {self.currency}"


class PaymentView(models.Model):
    """
    Each time someone opens a VyoPay payment link.
    Used for analytics (views, conversion rate, etc.).
    """
    payment_request = models.ForeignKey(
        "PaymentRequest",
        related_name="views",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(default=timezone.now)

    user_agent = models.TextField(blank=True, null=True)
    referer = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    country = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)

    device_type = models.CharField(max_length=50, blank=True, null=True)  # e.g. mobile / desktop
    platform = models.CharField(max_length=50, blank=True, null=True)    # e.g. iOS / Android / Windows

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"View for {self.payment_request.short_code} at {self.timestamp}"


class PaymentConversion(models.Model):
    """
    Whenever a user *starts* the payment (clicks Pay).
    Lets us measure drop-off before successful payment.
    """
    payment_request = models.ForeignKey(
        "PaymentRequest",
        related_name="conversions",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=100, blank=True, null=True)  # e.g. 'public_page', 'qr'

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Conversion for {self.payment_request.short_code} at {self.timestamp}"
