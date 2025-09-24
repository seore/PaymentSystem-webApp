from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('login/dashboard/', views.dashboard, name='dashboard'),
    path('send/', views.send_money, name='send_money'),
    path('request/', views.request_money, name='request_money'),
    path('transaction/', views.view_transactions, name='transaction_history'),
    path('conversion/<str:sender_currency>/<str:recipient_currency>/<str:amount>/', views.currency_conversion, name='currency_conversion'),

    # Admin
    path('admin/admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/registration_admin/', views.registration_admin, name='register_admin'),

    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset_form'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
