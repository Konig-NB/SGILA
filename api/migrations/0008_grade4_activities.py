from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_passwordresettoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='VocabularyQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=100)),
                ('option_1', models.CharField(max_length=200)),
                ('option_2', models.CharField(max_length=200)),
                ('option_3', models.CharField(max_length=200)),
                ('correct_answer', models.CharField(max_length=200)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vocabulary_questions', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='SequencingActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordered_events', models.TextField()),
                ('instruction', models.CharField(default='Put these events in the correct order.', max_length=300)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequencing_activities', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='InferenceQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('option_1', models.CharField(max_length=200)),
                ('option_2', models.CharField(max_length=200)),
                ('option_3', models.CharField(max_length=200)),
                ('option_4', models.CharField(max_length=200)),
                ('correct_answer', models.CharField(max_length=200)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inference_questions', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='PredictionQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stop_point_text', models.TextField()),
                ('question', models.CharField(default='What do you think will happen next?', max_length=300)),
                ('option_1', models.CharField(max_length=200)),
                ('option_2', models.CharField(max_length=200)),
                ('option_3', models.CharField(max_length=200)),
                ('option_4', models.CharField(max_length=200)),
                ('correct_answer', models.CharField(max_length=200)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prediction_questions', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='FeelingsQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('option_1', models.CharField(max_length=100)),
                ('option_2', models.CharField(max_length=100)),
                ('option_3', models.CharField(max_length=100)),
                ('option_4', models.CharField(max_length=100)),
                ('correct_answer', models.CharField(max_length=100)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feelings_questions', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='CauseEffectPair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cause', models.TextField()),
                ('effect', models.TextField()),
                ('order', models.IntegerField(default=0)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cause_effect_pairs', to='api.lesson')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='ThemeQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(default='What is the main lesson of the story?', max_length=300)),
                ('option_1', models.CharField(max_length=200)),
                ('option_2', models.CharField(max_length=200)),
                ('option_3', models.CharField(max_length=200)),
                ('option_4', models.CharField(max_length=200)),
                ('correct_answer', models.CharField(max_length=200)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='theme_questions', to='api.lesson')),
            ],
        ),
        migrations.CreateModel(
            name='WrittenResponsePrompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt', models.TextField()),
                ('guidance', models.CharField(blank=True, help_text="E.g. 'Write 3 to 4 sentences.'", max_length=300)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='written_prompts', to='api.lesson')),
            ],
        ),
    ]
