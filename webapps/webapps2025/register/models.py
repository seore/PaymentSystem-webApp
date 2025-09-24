from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from payapp.constants import CURRENCY_CHOICES


class AdminProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Admin Profile"


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
