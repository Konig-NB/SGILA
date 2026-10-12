import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()
from api.models import Lesson, StoryPage
for title in ["A Dog's Life", "A New Baby", "The School Shed Is on Fire", "Dan's Bad Week", "Spring Day Surprise"]:
    lesson = Lesson.objects.get(title=title)
    print(f'{title}:')
    for page in lesson.pages.all():
        print(f'  Page {page.page_number}: {page.image_url}')