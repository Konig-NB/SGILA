from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_subscription_payment_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PackageCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=32, unique=True)),
                ('label', models.CharField(blank=True, max_length=160)),
                ('max_redemptions', models.PositiveIntegerField(default=1)),
                ('redemptions_count', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plan_type',
            field=models.CharField(choices=[('individual', 'Individual (Parent)'), ('family', 'Family (Parent)'), ('enterprise', 'Enterprise (School)')], max_length=20),
        ),
        migrations.AddField(
            model_name='subscription',
            name='package_code',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscriptions', to='api.packagecode'),
        ),
    ]
