# Generated for the citizen service catalog.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0002_rename_diagnosis_name_diagnosis_name_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MainService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("google_form_url", models.URLField(verbose_name="Google Form link")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "main_service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="services",
                        to="med.mainservice",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
    ]
