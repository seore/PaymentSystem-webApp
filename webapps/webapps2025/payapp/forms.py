from django import forms
from .models import PaymentRequest


class PaymentRequestForm(forms.ModelForm):
    """
    Form used on the "Create payment link" screen.
    We expose expiry_days as a simple integer and compute expires_at in the view.
    """
    expiry_days = forms.IntegerField(
        min_value=1,
        max_value=365,
        initial=7,
        help_text="After this many days, the link will no longer accept payments.",
        label="Expiry (days)",
    )

    class Meta:
        model = PaymentRequest
        fields = ["amount", "currency", "description", "expiry_days"]

        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
            "currency": forms.TextInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
