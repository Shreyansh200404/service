import uuid

import django.core.validators
import med.models
from django.db import migrations, models


def backfill_request_references(apps, schema_editor):
    registration_request_model = apps.get_model("med", "RegistrationRequest")
    for registration_request in registration_request_model.objects.filter(
        reference_number__isnull=True
    ):
        registration_request.reference_number = f"REQ-{uuid.uuid4().hex[:20].upper()}"
        registration_request.save(update_fields=["reference_number"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0007_registrationrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationrequest",
            name="phone_number",
            field=models.CharField(
                default="",
                max_length=25,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a valid phone number.",
                        regex=r"^\+?[0-9][0-9\s().-]{6,23}$",
                    ),
                ],
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="registrationrequest",
            name="reference_number",
            field=models.CharField(blank=True, max_length=24, null=True, unique=True),
        ),
        migrations.RunPython(backfill_request_references, noop_reverse),
        migrations.AlterField(
            model_name="registrationrequest",
            name="reference_number",
            field=models.CharField(
                default=med.models.generate_registration_reference,
                editable=False,
                max_length=24,
                unique=True,
            ),
        ),
        migrations.CreateModel(
            name="PortalContactDetails",
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
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("whatsapp_number", models.CharField(blank=True, max_length=30)),
                ("instagram_id", models.CharField(blank=True, max_length=100)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
