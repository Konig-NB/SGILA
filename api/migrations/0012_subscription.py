from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_type', models.CharField(choices=[('individual', 'Individual (Parent)'), ('enterprise', 'Enterprise (School)')], max_length=20)),
                ('billing_cycle', models.CharField(blank=True, choices=[('monthly', 'Monthly'), ('annual', 'Annual')], max_length=10)),
                ('status', models.CharField(choices=[('trial', 'Free trial'), ('pending', 'Pending — awaiting payment/approval'), ('active', 'Active'), ('cancelled', 'Cancelled')], default='trial', max_length=12)),
                ('school_name', models.CharField(blank=True, max_length=200)),
                ('district_or_province', models.CharField(blank=True, max_length=160)),
                ('estimated_learners', models.IntegerField(blank=True, null=True)),
                ('contact_name', models.CharField(blank=True, max_length=120)),
                ('contact_phone', models.CharField(blank=True, max_length=30)),
                ('funding_source', models.CharField(blank=True, max_length=160)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to='api.parent')),
                ('teacher', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to='api.teacher')),
            ],
        ),
    ]
