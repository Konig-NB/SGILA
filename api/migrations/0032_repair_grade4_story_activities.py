import ast
import json

from django.db import migrations


ACTIVITY_GROUP_TITLES = {
    'word_scramble': 'Spelling Activity',
    'matching': 'Word Detective',
    'cloze': 'Story Words',
    'sequencing': 'Sequencing',
}


def repair_grade4_activities(apps, schema_editor):
    Lesson = apps.get_model('api', 'Lesson')
    ReadingActivity = apps.get_model('api', 'ReadingActivity')
    database = schema_editor.connection.alias
    lesson_ids = Lesson.objects.using(database).filter(
        grade=4,
        is_ai_generated=True,
    ).values_list('id', flat=True)

    activities = ReadingActivity.objects.using(database).filter(
        lesson_id__in=lesson_ids,
        activity_type__in=['matching', 'word_scramble', 'crossword'],
    )
    for activity in activities.iterator():
        try:
            answer = json.loads(activity.correct_answer or '')
        except (TypeError, json.JSONDecodeError):
            try:
                answer = ast.literal_eval(activity.correct_answer)
            except (SyntaxError, ValueError, TypeError):
                continue
        if isinstance(answer, (dict, list)):
            activity.correct_answer = json.dumps(answer, ensure_ascii=False)
            activity.save(update_fields=['correct_answer'], using=database)

    for lesson_id in lesson_ids:
        grouped_activities = ReadingActivity.objects.using(database).filter(
            lesson_id=lesson_id,
            group_number=2,
            group_title='Word Fun & Practice',
        ).order_by('order', 'id')
        for group_number, activity in enumerate(grouped_activities, start=2):
            activity.group_number = group_number
            activity.group_title = ACTIVITY_GROUP_TITLES.get(
                activity.activity_type,
                'Word Fun & Practice',
            )
            activity.save(update_fields=['group_number', 'group_title'], using=database)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_alter_storypage_lesson'),
    ]

    operations = [
        migrations.RunPython(repair_grade4_activities, migrations.RunPython.noop),
    ]