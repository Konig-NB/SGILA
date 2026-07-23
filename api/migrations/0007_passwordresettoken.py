from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_otptoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('role', models.CharField(choices=[('parent', 'Parent'), ('teacher', 'Teacher')], max_length=10)),
                ('token', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_used', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
