from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Transaction, CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'first_name', 'last_name', 'email', 'currency', 'is_staff', 'is_superuser')
    list_filter = ('currency', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('is_superuser'):
            obj.is_staff = True
        super().save_model(request, obj, form, change)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'amount', 'status', 'timestamp', 'converted_amount', 'converted_currency')
    list_filter = ('status', 'timestamp')
    search_fields = ('sender__username', 'recipient__username', 'status')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
