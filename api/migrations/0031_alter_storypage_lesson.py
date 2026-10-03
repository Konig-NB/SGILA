import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_lesson_character_description_alter_storypage_lesson'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storypage',
            name='lesson',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pages',
                to='api.lesson',
            ),
        ),
    ]