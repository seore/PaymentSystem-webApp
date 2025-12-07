from django.urls import path
from . import views

app_name = "payapp"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("payments/new/", views.create_payment_request, name="payment_new"),
    path("payments/<str:short_code>/", views.payment_link_detail, name="payment_detail"),
    path("pay/<str:short_code>/", views.public_pay_page, name="public_pay"),
    path("payments/success/", views.payment_success, name="payment_success"),
    path("payments/failed/", views.payment_failed, name="payment_failed"),

    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
