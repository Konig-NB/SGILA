from collections import Counter

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from api.curriculum_enrichment import LESSON_COVERS
from api.grade1_activity_blueprints import GRADE_ONE_ACTIVITY_BLUEPRINTS
from api.models import Lesson, ReadingActivity


EXPECTED_GROUP_TITLES = {
    1: 'Phonics & Story-Word Spelling',
    2: 'Short Sentences & Picture Matching',
    3: 'Opposites & Contrasting Concepts',
}


class GradeOneBlueprintTests(SimpleTestCase):
    def test_every_story_has_three_groups_of_three_questions(self):
        self.assertEqual(len(GRADE_ONE_ACTIVITY_BLUEPRINTS), 5)
        for title, activities in GRADE_ONE_ACTIVITY_BLUEPRINTS.items():
            with self.subTest(title=title):
                self.assertEqual(len(activities), 9)
                self.assertEqual(
                    Counter(activity['group_number'] for activity in activities),
                    Counter({1: 3, 2: 3, 3: 3}),
                )
                for activity in activities:
                    self.assertEqual(
                        activity['group_title'],
                        EXPECTED_GROUP_TITLES[activity['group_number']],
                    )

    def test_grade_one_blueprints_do_not_use_old_activity_types(self):
        old_types = {ReadingActivity.SEQUENCING, ReadingActivity.TRUE_FALSE}
        for title, activities in GRADE_ONE_ACTIVITY_BLUEPRINTS.items():
            with self.subTest(title=title):
                self.assertFalse({item['activity_type'] for item in activities} & old_types)


class SyncGradeOneActivitiesTests(TestCase):
    def test_command_replaces_only_grade_one_reading_activities(self):
        for title in GRADE_ONE_ACTIVITY_BLUEPRINTS:
            lesson = Lesson.objects.create(title=title, grade=1)
            ReadingActivity.objects.create(
                lesson=lesson,
                activity_type=ReadingActivity.TRUE_FALSE,
                skill='literal_comprehension',
                question='Old question',
                correct_answer='True',
            )

        grade_two = Lesson.objects.create(title='Grade 2 story', grade=2)
        untouched = ReadingActivity.objects.create(
            lesson=grade_two,
            activity_type=ReadingActivity.TRUE_FALSE,
            skill='literal_comprehension',
            question='Keep this question',
            correct_answer='True',
        )

        call_command('sync_grade1_activities', verbosity=0)

        for title in GRADE_ONE_ACTIVITY_BLUEPRINTS:
            lesson = Lesson.objects.get(title=title, grade=1)
            activities = list(lesson.reading_activities.order_by('order'))
            self.assertEqual(len(activities), 9)
            self.assertEqual(
                Counter(activity.group_number for activity in activities),
                Counter({1: 3, 2: 3, 3: 3}),
            )
            self.assertEqual(lesson.thumbnail_image, LESSON_COVERS[title])
        self.assertTrue(ReadingActivity.objects.filter(pk=untouched.pk).exists())
