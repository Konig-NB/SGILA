from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_subscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('card', 'Debit/Credit card'), ('debit_order', 'Bank debit order')], max_length=20),
        ),
        migrations.AddField(
            model_name='subscription',
            name='payer_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='subscription',
            name='card_last4',
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name='subscription',
            name='card_expiry',
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name='subscription',
            name='bank_name',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='subscription',
            name='account_last4',
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name='subscription',
            name='branch_code',
            field=models.CharField(blank=True, max_length=10),
        ),
    ]
