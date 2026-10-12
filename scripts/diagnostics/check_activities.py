import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()
from api.models import ReadingActivity
for a in ReadingActivity.objects.filter(group_title__in=['Visual Matching', 'Fix the Mistake']):
    opts = a.get_options()
    print(f'--- ID {a.id}: {a.group_title} ---')
    print(f'  question: {a.question}')
    print(f'  activity_type: {a.activity_type}')
    if isinstance(opts, dict):
        print(f'  options instruction: {opts.get("instruction", "MISSING")}')
        print(f'  options audio_text: {opts.get("audio_text", "MISSING")}')
    else:
        print(f'  options type: {type(opts)}')
