import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0029_grade4_story_framework'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='character_description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='storypage',
            name='lesson',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='api.lesson',
            ),
        ),
    ]