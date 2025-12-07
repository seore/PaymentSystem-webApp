import secrets
import stripe

from datetime import timedelta

from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import logout
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseBadRequest

from .models import PaymentRequest, Transaction, PaymentView, PaymentConversion


stripe.api_key = settings.STRIPE_SECRET_KEY


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

    transactions = (
        Transaction.objects
        .filter(payment_request__merchant=request.user)
        .select_related("payment_request")
        .order_by("-created_at")[:20]
    )

    # Simple analytics: last 7 days views & payments
    from datetime import timedelta
    today = timezone.now().date()
    week_ago = today - timedelta(days=6)

    views_qs = (
        PaymentView.objects
        .filter(payment_request__merchant=request.user,
                timestamp__date__gte=week_ago)
        .annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    paid_qs = (
        Transaction.objects
        .filter(payment_request__merchant=request.user,
                status=Transaction.STATUS_SUCCESS,
                created_at__date__gte=week_ago)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    # Build arrays for Chart.js
    labels = []
    views_data = []
    paid_data = []

    day_index = {v["day"]: v["count"] for v in views_qs}
    paid_index = {p["day"]: p["count"] for p in paid_qs}

    for i in range(7):
        d = week_ago + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        views_data.append(day_index.get(d, 0))
        paid_data.append(paid_index.get(d, 0))

    context = {
        "payment_requests": payment_requests[:10],
        "transactions": transactions,
        "summary": summary,
        "chart_labels": labels,
        "chart_views": views_data,
        "chart_paid": paid_data,
    }
    return render(request, "payapp/dashboard.html", context)



@login_required
@require_http_methods(["GET", "POST"])
def create_payment_request(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        currency = request.POST.get("currency", "GBP").upper()
        description = request.POST.get("description", "")
        expiry_days = request.POST.get("expiry_days") or "7"

        try:
            expiry_days = int(expiry_days)
        except ValueError:
            expiry_days = 7

        short_code = _generate_short_code()
        expires_at = timezone.now() + timedelta(days=expiry_days)

        payment_request = PaymentRequest.objects.create(
            merchant=request.user,
            short_code=short_code,
            amount=amount,
            currency=currency,
            description=description,
            expires_at=expires_at,
        )

        return redirect("payapp:payment_detail", short_code=payment_request.short_code)

    return render(request, "payapp/payment_new.html")



@login_required
def payment_link_detail(request, short_code):
    payment = get_object_or_404(
        PaymentRequest,
        short_code=short_code,
        merchant=request.user,
    )

    payment_url = request.build_absolute_uri(
        reverse("payapp:public_pay", args=[payment.short_code])
    )

    context = {
        "payment": payment,
        "payment_url": payment_url,
    }
    return render(request, "payapp/payment_detail.html", context)


@require_http_methods(["GET", "POST"])
def public_pay_page(request, short_code):
    payment_request = get_object_or_404(PaymentRequest, short_code=short_code)

    # If expired, mark and show expired page
    if payment_request.is_expired():
        payment_request.status = PaymentRequest.STATUS_EXPIRED
        payment_request.save(update_fields=["status"])
        return render(request, "payapp/payment_expired.html", {"payment": payment_request})

    # 🔹 Track a view every time this page is opened (GET or POST)
    PaymentView.objects.create(
        payment_request=payment_request,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referer=request.META.get("HTTP_REFERER", ""),
        # country / city / device_type / platform can be filled later using UA/geo libs
    )

    if request.method == "POST":
        # 🔹 Track that the user started the payment flow
        PaymentConversion.objects.create(
            payment_request=payment_request,
            source="public_page",
        )

        # existing Stripe Checkout logic here
        success_url = request.build_absolute_uri(
            reverse("payapp:payment_success")
        ) + "?session_id={CHECKOUT_SESSION_ID}"

        cancel_url = request.build_absolute_uri(
            reverse("payapp:payment_failed")
        )

        amount_in_minor = int(payment_request.amount * 100)

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": payment_request.currency.lower(),
                        "product_data": {
                            "name": payment_request.description or f"Payment {payment_request.short_code}",
                        },
                        "unit_amount": amount_in_minor,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "short_code": payment_request.short_code,
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return redirect(session.url, code=303)

    # GET → just render page
    return render(request, "payapp/public_pay.html", {"payment": payment_request})


@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    We care about: checkout.session.completed
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        # If you haven't set it yet, just ignore for now
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        # Invalid payload
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponseBadRequest("Invalid signature")

    # Handle the event type
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        short_code = session.get("metadata", {}).get("short_code")
        amount_total = session.get("amount_total")  # in minor units
        currency = session.get("currency", "gbp").upper()
        provider_txn_id = session.get("payment_intent") or session.get("id")

        if short_code:
            try:
                payment_request = PaymentRequest.objects.get(short_code=short_code)
            except PaymentRequest.DoesNotExist:
                payment_request = None

            if payment_request:
                # Mark as paid
                payment_request.status = PaymentRequest.STATUS_PAID
                payment_request.save(update_fields=["status"])

                # Create transaction record
                Transaction.objects.create(
                    payment_request=payment_request,
                    status=Transaction.STATUS_SUCCESS,
                    amount=(amount_total or 0) / 100 if amount_total else payment_request.amount,
                    currency=currency,
                    provider_txn_id=provider_txn_id or "",
                    raw_response=event,
                )

    # Return a 200 response to acknowledge receipt
    return HttpResponse(status=200)



def payment_success(request):
    return render(request, "payapp/payment_success.html")


def payment_failed(request):
    return render(request, "payapp/payment_failed.html")


def logout_view(request):
    """
    Simple logout that works with a GET and redirects to login.
    """
    logout(request)
    return redirect("login")

