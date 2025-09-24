from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, AdminProfile


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'currency', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('currency', 'is_staff')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'currency')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'currency', 'password1', 'password2'),
        }),
    )


class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_admin')
    search_fields = ('user__username',)


# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(AdminProfile, AdminProfileAdmin)

