#!/usr/bin/env python
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from django.conf import settings

print("USE_POSTGRES env var:", os.environ.get('USE_POSTGRES', 'NOT SET'))
print("DATABASE ENGINE:", settings.DATABASES['default']['ENGINE'])
print("DATABASE NAME:", settings.DATABASES['default'].get('NAME', 'NOT SET'))
