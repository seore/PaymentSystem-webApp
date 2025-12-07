from django.contrib import admin
from .models import PaymentRequest, Transaction


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("short_code", "merchant", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("short_code", "merchant__username", "description")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_request", "status", "amount", "currency", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "provider_txn_id", "payment_request__short_code")
