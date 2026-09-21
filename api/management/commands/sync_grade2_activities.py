"""Load every Grade 2 activity from the spec document into the database.

Run it from the folder that holds manage.py::

    python manage.py sync_grade2_activities

The command is safe to run as often as you like: it clears the old Grade 2
activities for each story first, then writes the five activity groups from
api/grade2_activity_blueprints.py in the document's order. Nothing outside
Grade 2 is touched.
"""

import json
from copy import deepcopy

from django.core.management.base import BaseCommand
from django.db import transaction

from api.grade2_activity_blueprints import (
    ACTIVITY_GROUPS,
    GRADE_TWO_ACTIVITY_BLUEPRINTS,
)
from api.models import (
    ComprehensionQuestion,
    Lesson,
    ReadingActivity,
    SpellingActivity,
    VisualActivityItem,
)


class Command(BaseCommand):
    help = 'Replace the Grade 2 activities with the five groups from the Grade 2 spec document.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--story',
            dest='story',
            default='',
            help='Only reload one story, by its exact lesson title.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        wanted = (options.get('story') or '').strip()
        updated = 0
        missing = []

        for title, blueprint in GRADE_TWO_ACTIVITY_BLUEPRINTS.items():
            if wanted and title != wanted:
                continue

            lessons = Lesson.objects.filter(grade=2, title=title)
            if not lessons.exists():
                missing.append(title)
                continue

            for lesson in lessons:
                self.reload_lesson(lesson, blueprint)
                updated += 1

            counts = ' · '.join(
                f'{name} {sum(1 for a in blueprint if a["group_number"] == number)}'
                for number, name in ACTIVITY_GROUPS
            )
            self.stdout.write(f'  {title}: {counts}')

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {len(ACTIVITY_GROUPS)} activity groups into {updated} Grade 2 lesson(s).'
        ))
        if missing:
            self.stdout.write(self.style.WARNING(
                'No lesson found in the database for: ' + ', '.join(missing)
                + '. Add the story first, then run this command again.'
            ))

    # ------------------------------------------------------------------
    def reload_lesson(self, lesson, blueprint):
        """Write one story's five activity groups, replacing whatever was there."""
        lesson.reading_activities.all().delete()
        for order, activity in enumerate(blueprint, start=1):
            ReadingActivity.objects.create(
                lesson=lesson,
                order=order,
                **deepcopy(activity),
            )

        # The learner's questions flow reads ReadingActivity, but the older
        # stand-alone pages (comprehension, visual matching, spelling) and the
        # progress report still read these tables. Keep them saying the same
        # thing as the document so no screen disagrees with another.
        self.mirror_comprehension(lesson, blueprint)
        self.mirror_visual(lesson, blueprint)
        self.mirror_spelling(lesson, blueprint)

    @staticmethod
    def group(blueprint, number):
        return [a for a in blueprint if a['group_number'] == number]

    def mirror_comprehension(self, lesson, blueprint):
        lesson.questions.all().delete()
        for activity in self.group(blueprint, 1):
            choices = list(activity['options'].get('choices') or [])
            choices = (choices + ['', '', '', ''])[:4]
            ComprehensionQuestion.objects.create(
                lesson=lesson,
                question=activity['question'],
                option_1=choices[0],
                option_2=choices[1],
                option_3=choices[2],
                option_4=choices[3],
                correct_answer=activity['correct_answer'],
            )

    def mirror_visual(self, lesson, blueprint):
        lesson.visual_items.all().delete()
        for activity in self.group(blueprint, 4):
            config = activity['options']
            VisualActivityItem.objects.create(
                lesson=lesson,
                image_url=config.get('prompt_image', ''),
                correct_word=activity['correct_answer'],
                word_options=','.join(config.get('choices') or []),
            )

    def mirror_spelling(self, lesson, blueprint):
        lesson.spelling_activities.all().delete()
        for activity in self.group(blueprint, 5):
            config = activity['options']
            image = config.get('prompt_image', '')

            if activity['activity_type'] == 'word_scramble':
                answer = next(iter(json.loads(activity['correct_answer']).values()))
                SpellingActivity.objects.create(
                    lesson=lesson,
                    activity_type=SpellingActivity.DRAG_LETTERS,
                    display_text=','.join(config['items'][0]['scramble']),
                    answer=answer,
                    image_url=image,
                )
            elif config.get('presentation') == 'grade1_phonics':
                SpellingActivity.objects.create(
                    lesson=lesson,
                    activity_type=SpellingActivity.FILL_VOWEL,
                    display_text=config['display_word'],
                    answer=config['audio_text'],
                    image_url=image,
                )
            else:
                choices = ' / '.join(config.get('choices') or [])
                SpellingActivity.objects.create(
                    lesson=lesson,
                    activity_type=SpellingActivity.FILL_VOWEL,
                    display_text=f'Which word is spelled correctly? {choices}',
                    answer=activity['correct_answer'],
                    image_url=image,
                )
