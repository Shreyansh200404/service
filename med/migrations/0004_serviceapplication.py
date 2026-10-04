# Generated for user service application tracking.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0003_mainservice_service"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceApplication",
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
                ("applicant_name", models.CharField(max_length=150)),
                ("applicant_email", models.EmailField(blank=True, max_length=254)),
                ("service_name", models.CharField(max_length=150)),
                (
                    "payment_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("waived", "Waived"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=12,
                    ),
                ),
                (
                    "work_status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("on_hold", "On hold"),
                            ("rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="submitted",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="applications",
                        to="med.service",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="service_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
