from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class PaymentForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.all())
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = User.objects.exclude(id=user.id)


class RequestForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.all())
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = User.objects.exclude(id=user.id)
