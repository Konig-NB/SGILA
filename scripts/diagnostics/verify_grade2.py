import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

grade2_lessons = Lesson.objects.filter(grade=2).order_by('id')
for lesson in grade2_lessons:
    print(f"\n=== {lesson.title} ===")
    print(f"  Comprehension Questions: {lesson.questions.count()}")
    print(f"  Reading Activities: {lesson.reading_activities.count()}")
    for ra in lesson.reading_activities.all().order_by('order'):
        print(f"    {ra.order}: {ra.activity_type} ({ra.group_title}) - {ra.question[:50]}...")
    print(f"  Sequencing Activities: {lesson.sequencing_activities.count()}")
    for sa in lesson.sequencing_activities.all():
        print(f"    {sa.ordered_events[:60]}...")
    print(f"  Spelling Activities: {lesson.spelling_activities.count()}")
    for sa in lesson.spelling_activities.all():
        print(f"    {sa.activity_type}: {sa.display_text[:40]} -> {sa.answer}")
    print(f"  Visual Items: {lesson.visual_items.count()}")
    for vi in lesson.visual_items.all():
        print(f"    {vi.correct_word}: {vi.word_options[:40]}")