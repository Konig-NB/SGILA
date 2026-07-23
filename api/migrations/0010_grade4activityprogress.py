from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_alter_predictionquestion_stop_point_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='Grade4ActivityProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('completed_on', models.DateTimeField(auto_now_add=True)),

                # Activity 1 — Comprehension Questions
                ('comprehension_score', models.IntegerField(default=0)),
                ('comprehension_total', models.IntegerField(default=0)),

                # Activity 2 — Sequencing
                ('sequencing_score', models.IntegerField(default=0)),
                ('sequencing_total', models.IntegerField(default=0)),

                # Activity 3 — Inference
                ('inference_score', models.IntegerField(default=0)),
                ('inference_total', models.IntegerField(default=0)),

                # Activity 4 — Feelings
                ('feelings_score', models.IntegerField(default=0)),
                ('feelings_total', models.IntegerField(default=0)),

                # Activity 5 — Cause & Effect
                ('cause_effect_score', models.IntegerField(default=0)),
                ('cause_effect_total', models.IntegerField(default=0)),

                # Activity 6 — Theme / Main Lesson
                ('theme_score', models.IntegerField(default=0)),
                ('theme_total', models.IntegerField(default=0)),

                # Totals
                ('total_score', models.IntegerField(default=0)),
                ('total_possible', models.IntegerField(default=0)),
                ('stars_earned', models.IntegerField(default=0)),

                ('child', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='g4_progress',
                    to='api.child',
                )),
                ('lesson', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='g4_progress',
                    to='api.lesson',
                )),
            ],
            options={
                'ordering': ['-completed_on'],
            },
        ),
    ]
