import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import Lesson, ReadingActivity, ComprehensionQuestion

lesson = Lesson.objects.get(title="A Dog's Life")

# Check what the questions endpoint would return
activities = list(lesson.reading_activities.all())
print(f"Reading activities count: {len(activities)}")
for a in activities:
    print(f"  {a.id}: {a.activity_type} - group_number={a.group_number} - {a.question[:50]}")

print()

# Also check questions
questions = lesson.questions.all()
print(f"Comprehension questions count: {questions.count()}")
for q in questions:
    print(f"  {q.id}: {q.question[:50]}")