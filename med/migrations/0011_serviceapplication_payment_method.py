from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("med", "0010_passwordresetotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceapplication",
            name="payment_method",
            field=models.CharField(
                choices=[("phonepe", "PhonePe / UPI"), ("wallet", "Wallet")],
                db_index=True,
                default="wallet",
                max_length=20,
            ),
        ),
    ]
