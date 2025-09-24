from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from payapp.constants import CURRENCY_CHOICES


class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'currency', 'password1', 'password2']
