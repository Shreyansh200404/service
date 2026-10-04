import django.core.validators
from django.db import migrations, models


def mark_old_pending_as_unpaid(apps, schema_editor):
    application_model = apps.get_model("med", "ServiceApplication")
    application_model.objects.filter(payment_status="pending").update(
        payment_status="unpaid"
    )


def restore_pending_status(apps, schema_editor):
    application_model = apps.get_model("med", "ServiceApplication")
    application_model.objects.filter(payment_status="unpaid").update(
        payment_status="pending"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0005_service_amount_serviceapplication_amount_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="payment_qr_image",
            field=models.FileField(
                blank=True,
                help_text="Upload the PhonePe payment QR image for this service.",
                null=True,
                upload_to="service_payment_qr/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        ["png", "jpg", "jpeg", "webp"]
                    ),
                ],
            ),
        ),
        migrations.AddField(
            model_name="serviceapplication",
            name="transaction_ref",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(mark_old_pending_as_unpaid, restore_pending_status),
        migrations.AlterField(
            model_name="serviceapplication",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("unpaid", "Unpaid"),
                    ("verification_pending", "Awaiting verification"),
                    ("paid", "Paid"),
                    ("waived", "Waived"),
                ],
                db_index=True,
                default="unpaid",
                max_length=20,
            ),
        ),
    ]
