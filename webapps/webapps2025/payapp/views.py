import secrets
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import PaymentRequest, Transaction


def _generate_short_code() -> str:
    return secrets.token_urlsafe(6)[:8]


@login_required
def dashboard(request):
    payment_requests = PaymentRequest.objects.filter(merchant=request.user)

    summary = payment_requests.aggregate(
        total_amount=Sum("amount"),
        total_paid=Sum("amount", filter=Q(status=PaymentRequest.STATUS_PAID)),
        count=Count("id"),
    )

    transactions = Transaction.objects.filter(
        payment_request__merchant=request.user
    ).select_related("payment_request")[:20]

    context = {
        "payment_requests": payment_requests[:20],
        "transactions": transactions,
        "summary": summary,
    }
    return render(request, "payapp/dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def create_payment_request(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        currency = request.POST.get("currency", "GBP")
        description = request.POST.get("description", "")

        short_code = _generate_short_code()
        expires_at = timezone.now() + timedelta(days=7)

        PaymentRequest.objects.create(
            merchant=request.user,
            short_code=short_code,
            amount=amount,
            currency=currency,
            description=description,
            expires_at=expires_at,
        )
        return redirect("payapp:dashboard")

    return render(request, "payapp/payment_new.html")


@require_http_methods(["GET", "POST"])
def public_pay_page(request, short_code):
    payment_request = get_object_or_404(PaymentRequest, short_code=short_code)

    if payment_request.is_expired():
        payment_request.status = PaymentRequest.STATUS_EXPIRED
        payment_request.save(update_fields=["status"])
        return render(request, "payapp/payment_expired.html", {"payment": payment_request})

    if request.method == "POST":
        # TODO: integrate real payment gateway here.
        Transaction.objects.create(
            payment_request=payment_request,
            status=Transaction.STATUS_SUCCESS,
            amount=payment_request.amount,
            currency=payment_request.currency,
        )
        payment_request.status = PaymentRequest.STATUS_PAID
        payment_request.save(update_fields=["status"])
        return redirect("payapp:payment_success")

    return render(request, "payapp/public_pay.html", {"payment": payment_request})


def payment_success(request):
    return render(request, "payapp/payment_success.html")


def payment_failed(request):
    return render(request, "payapp/payment_failed.html")
