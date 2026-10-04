from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator
from django.db import models
from decimal import Decimal
from uuid import uuid4


def generate_registration_reference():
    return f"REQ-{uuid4().hex[:20].upper()}"


class Diagnosis(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class MainService(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    main_service = models.ForeignKey(
        MainService,
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    google_form_url = models.URLField("Google Form link")
    payment_qr_image = models.FileField(
        upload_to="service_payment_qr/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "webp"])],
        help_text="Upload the PhonePe payment QR image for this service.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Service fee in INR. Use 0 for a free service.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.main_service} — {self.name}"


class ServiceApplication(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("verification_pending", "Awaiting verification"),
        ("paid", "Paid"),
        ("waived", "Waived"),
    ]
    WORK_STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("on_hold", "On hold"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_applications",
    )
    applicant_name = models.CharField(max_length=150)
    applicant_email = models.EmailField(blank=True)
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    service_name = models.CharField(max_length=150)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    transaction_ref = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="unpaid",
        db_index=True,
    )
    work_status = models.CharField(
        max_length=12,
        choices=WORK_STATUS_CHOICES,
        default="submitted",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.user_id:
            self.applicant_name = (
                self.user.get_full_name() or self.user.get_username()
            )
            self.applicant_email = self.user.email or ""
        if self.service_id and not self.service_name:
            self.service_name = self.service.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.applicant_name} — {self.service_name}"

    @property
    def receipt_number(self):
        return f"CSP-{self.pk:06d}" if self.pk else ""


class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Account created"),
        ("rejected", "Rejected"),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=25,
        validators=[RegexValidator(
            regex=r"^\+?[0-9][0-9\s().-]{6,23}$",
            message="Enter a valid phone number.",
        )],
    )
    reason = models.TextField(blank=True)
    reference_number = models.CharField(
        max_length=24,
        unique=True,
        default=generate_registration_reference,
        editable=False,
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    credentials_sent_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_registration_requests",
    )

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.reference_number} — {self.full_name} ({self.email})"


class PortalContactDetails(models.Model):
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    instagram_id = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def whatsapp_url(self):
        digits = "".join(character for character in self.whatsapp_number if character.isdigit())
        return f"https://wa.me/{digits}" if digits else ""

    @property
    def instagram_url(self):
        handle = self.instagram_id.strip().lstrip("@")
        return f"https://www.instagram.com/{handle}/" if handle else ""

    def __str__(self):
        return "Portal contact details"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset OTP for {self.user_id}"