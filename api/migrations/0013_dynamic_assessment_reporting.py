from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_readingactivity'),
    ]

    operations = [
        migrations.AddField(
            model_name='progress',
            name='assessment_scores',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='readingactivity',
            name='group_number',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='readingactivity',
            name='group_title',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name='readingactivity',
            name='activity_type',
            field=models.CharField(
                choices=[
                    ('multiple_choice', 'Multiple choice'),
                    ('true_false', 'True or false'),
                    ('open_ended', 'Open-ended response'),
                    ('sequencing', 'Sequencing'),
                    ('matching', 'Matching'),
                    ('cloze', 'Fill in the blank'),
                    ('oral_response', 'Oral response'),
                    ('prediction', 'Prediction'),
                    ('reasoning', 'Reasoning'),
                    ('crossword', 'Crossword puzzle'),
                    ('word_scramble', 'Word scramble'),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='readingactivity',
            name='skill',
            field=models.CharField(
                choices=[
                    ('literal_comprehension', 'Literal comprehension'),
                    ('sequencing', 'Sequencing'),
                    ('inference', 'Inference'),
                    ('vocabulary_in_context', 'Vocabulary in context'),
                    ('prediction', 'Prediction'),
                    ('summarising', 'Summarising'),
                    ('character_motivation', 'Character motivation'),
                    ('text_to_self', 'Text-to-self connection'),
                    ('fact_vs_opinion', 'Fact versus opinion'),
                    ('spelling', 'Spelling'),
                ],
                max_length=40,
            ),
        ),
    ]
