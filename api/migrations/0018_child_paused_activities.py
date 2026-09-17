from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_merge_20260809_1203'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='paused_activities',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]