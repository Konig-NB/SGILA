from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_child_first_name_child_last_name_child_photo_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OTPToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('role', models.CharField(choices=[('parent', 'Parent'), ('teacher', 'Teacher')], max_length=10)),
                ('code', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_used', models.BooleanField(default=False)),
                ('pending_data', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
