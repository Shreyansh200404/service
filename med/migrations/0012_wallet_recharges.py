import decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def mark_existing_payments_as_upi(apps, schema_editor):
    ServiceApplication = apps.get_model("med", "ServiceApplication")
    ServiceApplication.objects.all().update(payment_method="phonepe")


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0011_serviceapplication_payment_method"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="service",
            name="payment_qr_image",
        ),
        migrations.RunPython(
            mark_existing_payments_as_upi,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="serviceapplication",
            name="payment_method",
            field=models.CharField(
                choices=[("phonepe", "PhonePe / UPI"), ("wallet", "Wallet")],
                db_index=True,
                default="wallet",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="WalletSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "payment_qr_image",
                    models.FileField(
                        blank=True,
                        help_text="Upload the QR code used only for wallet recharges.",
                        upload_to="wallet_recharge_qr/",
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                ["png", "jpg", "jpeg", "webp"]
                            )
                        ],
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserWallet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "balance",
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal("0.00"),
                        max_digits=12,
                        validators=[
                            django.core.validators.MinValueValidator(
                                decimal.Decimal("0.00")
                            )
                        ],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WalletRechargeRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(
                                decimal.Decimal("0.01")
                            )
                        ],
                    ),
                ),
                ("transaction_ref", models.CharField(max_length=100, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Awaiting verification"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=10,
                    ),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_wallet_recharges",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet_recharge_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.CreateModel(
            name="WalletTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                ("description", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "application",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="wallet_transaction",
                        to="med.serviceapplication",
                    ),
                ),
                (
                    "recharge_request",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="wallet_transaction",
                        to="med.walletrechargerequest",
                    ),
                ),
                (
                    "wallet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="med.userwallet",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
