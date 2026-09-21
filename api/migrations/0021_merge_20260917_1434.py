# Merge migration: reunites the two migration branches that both built on
# 0017_merge_20260809_1203. No schema changes — it only gives the migration
# graph a single leaf again so "manage.py migrate" and the tests can run.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_child_paused_activities'),
        ('api', '0020_merge_20260909_1720'),
    ]

    operations = [
    ]
