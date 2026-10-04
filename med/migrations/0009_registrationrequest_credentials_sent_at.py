from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0008_request_phone_reference_and_contacts"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationrequest",
            name="credentials_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
