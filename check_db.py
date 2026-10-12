import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()
from api.models import ReadingActivity

# Find Match It! activities
match_it = ReadingActivity.objects.filter(group_title='Match It!')
print(f"Found {match_it.count()} Match It! activities")
for a in match_it:
    print(f"\n--- Activity ID {a.id}, Lesson: {a.lesson.title} ---")
    print(f"activity_type: {a.activity_type}")
    print(f"question: {a.question}")
    print(f"options type: {type(a.options)}")
    print(f"options: {a.options}")
    print(f"get_options(): {a.get_options()}")
    opts = a.get_options()
    if isinstance(opts, dict):
        print(f"instruction in options: {opts.get('instruction', '(MISSING)')}")
