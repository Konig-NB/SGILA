from copy import deepcopy

from django.core.management.base import BaseCommand
from django.db import transaction

from api.curriculum_enrichment import LESSON_COVERS
from api.grade1_activity_blueprints import GRADE_ONE_ACTIVITY_BLUEPRINTS
from api.models import Lesson, ReadingActivity


class Command(BaseCommand):
    help = 'Replace only Grade 1 reading activities with the canonical three-by-three structure.'

    @transaction.atomic
    def handle(self, *args, **options):
        updated = 0
        skipped = []

        for title, blueprint in GRADE_ONE_ACTIVITY_BLUEPRINTS.items():
            lessons = Lesson.objects.filter(grade=1, title=title)
            if not lessons.exists():
                skipped.append(title)
                continue

            for lesson in lessons:
                lesson.reading_activities.all().delete()
                for order, activity_data in enumerate(blueprint, start=1):
                    ReadingActivity.objects.create(
                        lesson=lesson,
                        order=order,
                        **deepcopy(activity_data),
                    )
                cover_url = LESSON_COVERS[title]
                if lesson.thumbnail_image != cover_url:
                    lesson.thumbnail_image = cover_url
                    lesson.save(update_fields=['thumbnail_image'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Updated {updated} Grade 1 lessons with 3 activities and 3 questions per activity.'
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                'Skipped missing lessons: ' + ', '.join(skipped)
            ))
