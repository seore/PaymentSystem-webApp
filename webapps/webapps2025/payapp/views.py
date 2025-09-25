import requests
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal
from django.views.decorators.http import require_GET
from django.db import transaction as dj_tx
from django.db.models import Q
from .models import Account, Transaction, CustomUser
from .forms import PaymentForm, RequestForm
from .tasks import send_transaction_email
from django.contrib import messages

EXCHANGE_RATES = {
    "USD": {"EUR": Decimal(0.85), "GBP": Decimal(0.75)},
    "EUR": {"USD": Decimal(1.18), "GBP": Decimal(0.88)},
    "GBP": {"USD": Decimal(1.33), "EUR": Decimal(1.14)},
}

def _abs(request, path):
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{get_current_site(request).domain}{path}"

def is_admin(user):
    return user.is_authenticated and user.is_staff


# Admin Dashboard
@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='login')
def admin_dashboard(request):
    users = CustomUser.objects.filter(is_superuser=False)
    all_transactions = Transaction.objects.all()

    return render(request, 'admin/admin_dashboard.html', {'users': users, 'all_transactions': all_transactions})


@user_passes_test(lambda u: u.is_superuser)
def registration_admin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('registration_admin')

        user = CustomUser.objects.create_user(username=username, password=password, is_superuser=True, is_staff=True)
        user.save()

        messages.success(request, f"Administrator {username} has been successfully registered.")
        return redirect('admin_dashboard')

    return render(request, 'admin/registration_admin.html')


@login_required
def dashboard(request):
    # create or fetch the user's account
    account, _ = Account.objects.get_or_create(user=request.user)

    # pull the user's transactions (join recipient for fewer queries)
    transactions = (
        Transaction.objects
        .filter(sender=request.user)
        .select_related('recipient')
        .order_by('-timestamp')
    )

    # build display rows
    transaction_display_data = []
    for t in transactions:
        currency = t.converted_currency or getattr(request.user, 'currency', '')
        amount = t.converted_amount if t.converted_amount is not None else t.amount
        transaction_display_data.append({
            'recipient': t.recipient.username,
            'display_amount': f"{amount} {currency}",
            'status': t.status,
            'timestamp': t.timestamp,
        })

    # --- these must be OUTSIDE the loop ---
    total_transactions = transactions.count()
    last_transaction = transactions.first()
    currencies = [t.converted_currency or getattr(request.user, 'currency', '') for t in transactions]
    most_used_currency = max(set(currencies), key=currencies.count) if currencies else 'N/A'

    return render(request, 'payapp/dashboard.html', {
        'account': account,
        'transaction_display_data': transaction_display_data,
        'total_transactions': total_transactions,
        'last_transaction': last_transaction,
        'most_used_currency': most_used_currency,
    })


@login_required
@dj_tx.atomic
def send_money(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST, user=request.user)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            amount = Decimal(form.cleaned_data['amount'])

            sender_account, _ = Account.objects.get_or_create(user=request.user)
            recipient_account, _ = Account.objects.get_or_create(user=recipient)

            sender_currency = getattr(request.user, "currency", "USD")
            recipient_currency = getattr(recipient, "currency", sender_currency)

            # helper: enqueue notification emails only after commit succeeds
            def notify(txn, *, converted_amount=None, converted_currency=None):
                dash = _abs(request, reverse("dashboard"))
                amount_display = f"{sender_currency} {amount:,.2f}"
                converted_display = (
                    f"{converted_currency} {converted_amount:,.2f}"
                    if converted_amount is not None
                    else None
                )

                # Sender email
                if getattr(request.user, "email", None):
                    send_transaction_email.delay(
                        to_email=request.user.email,
                        subject=f"You sent {amount_display} to {recipient.username}",
                        template="emails/transaction.html",
                        context={
                            "heading": "Payment Sent",
                            "name": request.user.get_username(),
                            "line1": f"You sent {amount_display} to {recipient.username}.",
                            "amount_display": amount_display,
                            "converted_display": converted_display,
                            "reference": getattr(txn, "id", txn.pk),
                            "dashboard_url": dash,
                        },
                    )

                # Recipient email
                if getattr(recipient, "email", None):
                    recv_amount_display = converted_display or amount_display
                    send_transaction_email.delay(
                        to_email=recipient.email,
                        subject=f"You received {recv_amount_display} from {request.user.username}",
                        template="emails/transaction.html",
                        context={
                            "heading": "Payment Received",
                            "name": recipient.get_username(),
                            "line1": f"You received {recv_amount_display} from {request.user.username}.",
                            "amount_display": recv_amount_display,
                            "converted_display": None,
                            "reference": getattr(txn, "id", txn.pk),
                            "dashboard_url": dash,
                        },
                    )

            # Same-currency transfer
            if sender_currency == recipient_currency:
                if sender_account.balance < amount:
                    messages.error(request, 'Insufficient funds.')
                    return redirect('send_money')

                sender_account.balance -= amount
                recipient_account.balance += amount
                sender_account.save()
                recipient_account.save()

                txn = Transaction.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    amount=amount,
                    status='COMPLETED'
                )
                dj_tx.on_commit(lambda: notify(txn))
                messages.success(request, 'Payment has been successfully sent.')

            # Cross-currency transfer
            else:
                conversion_url = f"http://127.0.0.1:8000/conversion/{sender_currency}/{recipient_currency}/{amount}/"
                response = requests.get(conversion_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    converted_amount = Decimal(str(data['converted_amount']))
                    conversion_rate = Decimal(str(data['rate']))

                    if sender_account.balance < amount:
                        messages.error(request, 'Insufficient funds for conversion.')
                        return redirect('send_money')

                    sender_account.balance -= amount
                    recipient_account.balance += converted_amount
                    sender_account.save()
                    recipient_account.save()

                    txn = Transaction.objects.create(
                        sender=request.user,
                        recipient=recipient,
                        amount=amount,
                        converted_amount=converted_amount,
                        converted_currency=recipient_currency,
                        conversion_rate=conversion_rate,
                        status='COMPLETED'
                    )
                    dj_tx.on_commit(lambda: notify(txn, converted_amount=converted_amount, converted_currency=recipient_currency))
                    messages.success(request, 'Payment sent successfully!')
                else:
                    messages.error(request, "Currency conversion failed.")
                    return redirect('send_money')

            return redirect('dashboard')
    else:
        form = PaymentForm(user=request.user)

    return render(request, 'payapp/send_money.html', {'form': form})



@login_required
def request_money(request):
    if request.method == 'POST':
        form = RequestForm(request.POST, user=request.user)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']
            Transaction.objects.create(sender=request.user, recipient=recipient, amount=amount, status='PENDING')
            messages.success(request, 'Payment request sent successfully!')
            return redirect('dashboard')
    else:
        form = RequestForm(user=request.user)
    return render(request, 'payapp/request_money.html', {'form': form})


@login_required
def view_transactions(request):
    transactions = Transaction.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).order_by('-timestamp')
    return render(request, 'payapp/transaction_history.html', {'transactions': transactions})


@require_GET
def currency_conversion(request, sender_currency, recipient_currency, amount):
    try:
        amount = Decimal(amount)
    except:
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    if sender_currency == recipient_currency:
        return JsonResponse({'converted_amount': Decimal(amount), 'rate': 1.0}, status=200)

    if sender_currency not in EXCHANGE_RATES or recipient_currency not in EXCHANGE_RATES[sender_currency]:
        return JsonResponse({'error': 'Unsupported currency or conversion pair.'}, status=404)

    conversion_rate = EXCHANGE_RATES[sender_currency][recipient_currency]
    converted_amount = amount * conversion_rate

    return JsonResponse({
        'from': sender_currency,
        'to': recipient_currency,
        'rate': float(conversion_rate),
        'original_amount': float(amount),
        'converted_amount': float(converted_amount)
    }, status=200)
