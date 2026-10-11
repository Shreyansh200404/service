from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import (
    Diagnosis,
    MainService,
    Medicine,
    PortalContactDetails,
    RegistrationRequest,
    Service,
    ServiceApplication,
    WalletRechargeRequest,
    WalletSettings,
    WalletTransaction,
)


User = get_user_model()


class RegistrationRequestForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )

    class Meta:
        model = RegistrationRequest
        fields = ["full_name", "email", "phone_number", "reason"]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "name",
            }),
            "reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "type": "tel",
                "placeholder": "+91 98765 43210",
                "autocomplete": "tel",
            }),
        }


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
        self.fields["username"].help_text = "Assigned by the administrator."
        self.fields["password1"].help_text = "Share the initial password with the user securely."


class PortalContactDetailsForm(forms.ModelForm):
    class Meta:
        model = PortalContactDetails
        fields = ["phone_number", "email", "whatsapp_number", "instagram_id"]
        widgets = {
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "type": "tel",
            }),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "whatsapp_number": forms.TextInput(attrs={
                "class": "form-control",
                "type": "tel",
            }),
            "instagram_id": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "@your_instagram_id",
            }),
        }


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "Account email address",
        }),
    )


class PasswordResetConfirmForm(forms.Form):
    email = forms.EmailField(
        label="Account email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "Account email address",
        }),
    )
    otp = forms.CharField(
        label="6-digit email code",
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "Enter the 6-digit code from your email.")],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        }),
    )
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user:
            self.fields.pop("email")

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "The passwords do not match.")
        if password1 and self.user:
            try:
                validate_password(password1, self.user)
            except ValidationError as error:
                self.add_error("new_password1", error)
        return cleaned_data



class DiagnosisForm(forms.ModelForm):

    class Meta:

        model = Diagnosis

        fields = ['name']

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Diagnosis'
                }
            )

        }


class MedicineForm(forms.ModelForm):

    class Meta:

        model = Medicine

        fields = ['diagnosis', 'name', 'dosage']

        widgets = {

            'diagnosis': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Medicine Name'
                }
            ),

            'dosage': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Dosage'
                }
            ),

        }


class MainServiceForm(forms.ModelForm):
    class Meta:
        model = MainService
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "main_service",
            "name",
            "description",
            "google_form_url",
            "amount",
            "is_active",
        ]
        widgets = {
            "main_service": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "google_form_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://forms.google.com/...",
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }),
        }


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = ServiceApplication
        fields = ["payment_status", "work_status"]
        widgets = {
            "payment_status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "work_status": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }

    def clean_payment_status(self):
        payment_status = self.cleaned_data["payment_status"]
        if (
            payment_status == "paid"
            and self.instance.pk
            and self.instance.payment_status == "unpaid"
            and self.instance.amount > 0
            and not WalletTransaction.objects.filter(
                application=self.instance
            ).exists()
        ):
            raise forms.ValidationError(
                "Paid service applications must be charged through the wallet."
            )
        return payment_status


class WalletRechargeForm(forms.ModelForm):
    transaction_ref = forms.CharField(
        label="Payment transaction reference",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter the transaction reference / UTR",
            "autocomplete": "off",
        }),
        help_text="Your recharge will be credited after an administrator verifies it.",
    )

    class Meta:
        model = WalletRechargeRequest
        fields = ["amount", "transaction_ref"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Enter recharge amount",
            }),
        }

    def clean_transaction_ref(self):
        transaction_ref = self.cleaned_data["transaction_ref"].strip()
        if WalletRechargeRequest.objects.filter(
            transaction_ref__iexact=transaction_ref
        ).exists():
            raise forms.ValidationError(
                "This transaction reference has already been submitted."
            )
        return transaction_ref


class WalletSettingsForm(forms.ModelForm):
    class Meta:
        model = WalletSettings
        fields = ["payment_qr_image"]
        widgets = {
            "payment_qr_image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": ".png,.jpg,.jpeg,.webp",
            }),
        }

    def clean_payment_qr_image(self):
        payment_qr_image = self.cleaned_data.get("payment_qr_image")
        if payment_qr_image and payment_qr_image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The wallet recharge QR must be 5 MB or smaller.")
        return payment_qr_image