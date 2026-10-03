from collections import Counter
import re
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from api.curriculum_enrichment import LESSON_COVERS
from api.grade1_activity_blueprints import GRADE_ONE_ACTIVITY_BLUEPRINTS
from api.grade1_story_framework import (
    THEMES,
    build_grade1_activities,
    grade1_generation_preferences,
    validate_grade1_story,
)
from api.models import Lesson, ReadingActivity


EXPECTED_GROUP_TITLES = {
    1: 'Phonics & Story-Word Spelling',
    2: 'Short Sentences & Picture Matching',
    3: 'Story Sentence Completion',
}

EXPECTED_ACTIVITY_THREE = {
    "Lerato's Fruit Basket": [
        ('The apple is ..........', ['Red', 'Green'], 'Red'),
        ('The banana is ..........', ['Yellow', 'Blue'], 'Yellow'),
        ('Lerato wants to be ..........', ['Strong', 'Weak'], 'Strong'),
    ],
    'A Very Hot Day': [
        ('The day is ..........', ['Hot', 'Cold'], 'Hot'),
        ('Karabo jumps into the ..........', ['Pond', 'School'], 'Pond'),
        ('Karabo is .......... with Cathy.', ['Happy', 'Sad'], 'Happy'),
    ],
    'Ben Goes to School': [
        ('Ben goes to ..........', ['School', 'Home'], 'School'),
        ('The children are .......... together.', ['Singing', 'Sleeping'], 'Singing'),
        ('Jabu is .......... to see Ben.', ['Happy', 'Sad'], 'Happy'),
    ],
    "Olwethu's First Day": [
        ('Olwethu goes to ..........', ['School', 'The beach'], 'School'),
        ('Olwethu has new ..........', ['Shoes', 'Toys'], 'Shoes'),
        ('Olwethu feels .......... at first.', ['Scared', 'Happy'], 'Scared'),
    ],
    'Bongi Waits': [
        ('Bongi waits ..........', ['Outside', 'Inside'], 'Outside'),
        ('Bongi hugs ..........', ['Granny and Grandpa', 'The teacher'], 'Granny and Grandpa'),
        ('Bongi is ..........', ['Happy', 'Sad'], 'Happy'),
    ],
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

    def test_activity_three_matches_the_revised_question_specification(self):
        for title, expected_questions in EXPECTED_ACTIVITY_THREE.items():
            with self.subTest(title=title):
                activity_three = [
                    activity
                    for activity in GRADE_ONE_ACTIVITY_BLUEPRINTS[title]
                    if activity['group_number'] == 3
                ]
                actual_questions = [
                    (
                        activity['question'],
                        activity['options']['choices'],
                        activity['correct_answer'],
                    )
                    for activity in activity_three
                ]
                self.assertEqual(actual_questions, expected_questions)
                for activity in activity_three:
                    self.assertEqual(activity['options']['audio_text'], activity['question'])
                    self.assertEqual(
                        activity['options']['instruction'],
                        'Listen to the sentence, then choose the missing word.',
                    )


class GradeOneStoryValidationTests(SimpleTestCase):
    def test_validation_requires_short_multisentence_pages_and_repairs_activity_words(self):
        story = {
            'title': 'A Helpful Day',
            'character_description': 'A young learner with a blue shirt.',
            'pages': [
                {'text': 'Lebo finds a red button. She puts it beside her school bag.'},
                {'text': 'A small bird sits near the gate. Lebo sees its bright wing.'},
                {'text': 'Her friend brings a blue box. They keep the button safe inside.'},
            ],
        }

        validated = validate_grade1_story(story)

        self.assertEqual(len(validated['pages']), 3)
        self.assertEqual(len(validated['phonics_words']), 3)
        self.assertEqual(len(validated['vocabulary_words']), 3)
        self.assertEqual(len(validated['picture_match']), 3)
        self.assertEqual(
            [item['page_number'] for item in validated['picture_match']],
            [1, 2, 3],
        )
        self.assertTrue(all(12 <= len(page['text'].split()) <= 22 for page in validated['pages']))
        self.assertTrue(all(len(page['text'].split('. ')) >= 2 for page in validated['pages']))

    def test_validation_rejects_missing_pages_instead_of_inserting_repeated_filler(self):
        with self.assertRaisesRegex(ValueError, 'at least one page'):
            validate_grade1_story({'pages': []})

    def test_validation_repairs_page_count_and_page_text_shape(self):
        story = {
            'title': 'The Red Button',
            'pages': [
                {'text': 'Lebo finds a red button. She puts it beside her school bag today.'},
                {'text': 'A small bird rests near the gate. Lebo sees its bright wing.'},
                {'text': 'Mina takes the box home today. She gives it to her friend.'},
                {'text': 'An extra page is safely folded into the ending.'},
            ],
        }

        validated = validate_grade1_story(story)

        self.assertEqual(len(validated['pages']), 3)
        self.assertTrue(all(
            12 <= len(page['text'].split()) <= 22
            and 2 <= len(re.findall(r'(?<=[.!?])\s+', page['text'])) + 1 <= 3
            for page in validated['pages']
        ))

    def test_validation_rejects_short_pages_instead_of_adding_generic_filler(self):
        story = {
            'pages': [
                {'text': 'Amahle has a box. She cuts a red door.'},
                {'text': 'A small bird rests near the gate. Lebo sees its bright wing.'},
                {'text': 'Mina takes the box home today. She gives it to her friend.'},
            ],
        }

        with self.assertRaisesRegex(ValueError, '12-22 words'):
            validate_grade1_story(story)

    def test_grade_one_activity_variants_change_phonics_and_picture_vocabulary_mix(self):
        story = validate_grade1_story({
            'title': 'The Red Button',
            'pages': [
                {'text': 'A child finds a red button. It shines beside her blue bag.'},
                {'text': 'A small bird rests near the gate. Its bright wing moves in the wind.'},
                {'text': 'Mina takes the box home today. She gives it to her friend.'},
            ],
            'phonics_words': ['child', 'small', 'home'],
            'vocabulary_words': ['button', 'bird', 'box'],
        })
        story['picture_match'] = [
            {'sentence': 'A child finds a red button.', 'page_number': 1},
            {'sentence': 'A small bird rests near the gate.', 'page_number': 2},
            {'sentence': 'Mina takes the box home today.', 'page_number': 3},
        ]
        story = validate_grade1_story(story)

        for variant, expected_visual_count in (
            ('phonics', 0), ('mixed', 1), ('visual_vocabulary', 3),
        ):
            with self.subTest(variant=variant):
                story['_activity_variant'] = variant
                activities = build_grade1_activities(
                    story, ['page-1', 'page-2', 'page-3'],
                    ['object-1', 'object-2', 'object-3'],
                )
                group_one = [activity for activity in activities if activity['group_number'] == 1]
                visual_count = sum(
                    activity['options'].get('presentation') == 'grade1_vocabulary'
                    for activity in group_one
                )
                self.assertEqual(len(activities), 9)
                self.assertEqual(visual_count, expected_visual_count)
                self.assertTrue(all(len(activity['options']['choices']) == 3 for activity in group_one))


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

    def test_ai_story_generation_avoids_the_latest_theme_and_activity_variant(self):
        Lesson.objects.create(
            title='Recent AI story',
            grade=1,
            is_ai_generated=True,
            generation_metadata={
                'rag': {'theme': THEMES[0]},
                'activity_variant': 'phonics',
            },
        )

        with patch('api.grade1_story_framework.random.choice', side_effect=lambda choices: choices[0]):
            theme, recent_themes, _characters, activity_variant = grade1_generation_preferences()

        self.assertEqual(recent_themes, [THEMES[0]])
        self.assertNotEqual(theme, THEMES[0])
        self.assertNotEqual(activity_variant, 'phonics')
