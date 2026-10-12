import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()
from api.models import Lesson, ComprehensionQuestion, ReadingActivity, SequencingActivity, SpellingActivity, VisualActivityItem, PronunciationWord
for title in ["A Dog's Life", "A New Baby", "The School Shed Is on Fire", "Dan's Bad Week", "Spring Day Surprise"]:
    lesson = Lesson.objects.get(title=title)
    print(f'{title}:')
    print(f'  Comprehension questions: {lesson.questions.count()}')
    print(f'  Reading activities: {lesson.reading_activities.count()}')
    print(f'  Sequencing activities: {lesson.sequencing_activities.count()}')
    print(f'  Spelling activities: {lesson.spelling_activities.count()}')
    print(f'  Visual items: {lesson.visual_items.count()}')
    print(f'  Pronunciation words: {lesson.pronunciation_words.count()}')
    print()