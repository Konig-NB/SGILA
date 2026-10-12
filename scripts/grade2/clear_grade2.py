import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# First, clear all existing Grade 2 lesson activities
grade2_lessons = Lesson.objects.filter(grade=2)
for lesson in grade2_lessons:
    print(f"Clearing activities for: {lesson.title}")
    lesson.reading_activities.all().delete()
    lesson.sequencing_activities.all().delete()
    lesson.spelling_activities.all().delete()
    lesson.visual_items.all().delete()
    # Note: ComprehensionQuestion is a separate model not linked to reading_activities
    lesson.questions.all().delete()

print("All Grade 2 activities cleared!")