from collections import Counter
from unittest.mock import patch

from django.test import SimpleTestCase

from api.grade2_activity_blueprints import (
    GRADE_TWO_ACTIVITY_BLUEPRINTS,
    unscramble,
)


class GradeTwoSpellingScrambleTests(SimpleTestCase):
    def test_blueprint_scrambles_differ_from_targets_and_preserve_letters(self):
        for activities in GRADE_TWO_ACTIVITY_BLUEPRINTS.values():
            for activity in activities:
                if activity['activity_type'] != 'word_scramble':
                    continue

                item = activity['options']['items'][0]
                answer = item['key']
                scramble = item['scramble'].lower()
                with self.subTest(answer=answer):
                    self.assertNotEqual(scramble, answer)
                    self.assertEqual(Counter(scramble), Counter(answer))
                    self.assertIn(
                        ', '.join(item['scramble']),
                        activity['question'],
                    )

    @patch('api.grade2_activity_blueprints.random.shuffle', side_effect=lambda letters: None)
    def test_shuffle_that_keeps_target_order_falls_back_to_rotation(self, _shuffle):
        activity = unscramble('A New Baby', list('AAB'), 'AAB')
        scramble = activity['options']['items'][0]['scramble']

        self.assertNotEqual(scramble, 'AAB')
        self.assertEqual(Counter(scramble), Counter('AAB'))

    def test_words_without_a_distinct_permutation_remain_unchanged(self):
        for letters, word in [(['A'], 'A'), (['A', 'A', 'A'], 'AAA')]:
            with self.subTest(word=word):
                activity = unscramble('A New Baby', letters, word)
                item = activity['options']['items'][0]
                self.assertEqual(item['scramble'], word)
                self.assertEqual(Counter(item['scramble']), Counter(word))
