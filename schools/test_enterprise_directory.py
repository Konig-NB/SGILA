import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from lessons import pricing
from schools.context import finder_context
from schools.directory import search_school_directory
from schools.views import directory_result, school_search


@override_settings(SCHOOLS_SEARCH_RATE_LIMIT=0)
class EnterpriseDirectorySearchTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request_search(self, query):
        request = self.factory.get(
            '/api/schools/search/',
            {'q': query},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        response = school_search(request)
        return response.status_code, json.loads(response.content)

    def test_search_uses_available_teacher_directory_records(self):
        results = search_school_directory('bright future')
        self.assertTrue(results)
        self.assertTrue(
            any(record['school_name'] == 'BRIGHT FUTURE PRIMARY' for record in results)
        )

        status, payload = self.request_search('bright future')
        self.assertEqual(status, 200)
        self.assertGreater(payload['count'], 0)
        self.assertIn('BRIGHT FUTURE PRIMARY', {
            result['name'] for result in payload['results']
        })

    def test_search_matches_directory_locations_without_a_province_filter(self):
        status, payload = self.request_search('johannesburg')
        self.assertEqual(status, 200)
        self.assertGreater(payload['count'], 0)
        self.assertTrue(all(
            result['town'].casefold() == 'johannesburg'
            for result in payload['results']
        ))
        self.assertNotIn('province', payload)

    def test_two_character_search_matches_teacher_registration_minimum(self):
        status, payload = self.request_search('br')
        self.assertEqual(status, 200)
        self.assertGreater(payload['count'], 0)

    def test_directory_quantile_maps_to_configured_enterprise_price(self):
        result = directory_result({
            'school_name': 'EXAMPLE PRIMARY SCHOOL',
            'location': 'PRETORIA',
            'quantile': 'Q3',
        }, 0)

        self.assertEqual(result['display_label'], 'EXAMPLE PRIMARY SCHOOL, PRETORIA')
        self.assertEqual(result['price_school_type'], 'quintile_3')
        self.assertEqual(
            result['price_per_learner_month'],
            pricing.format_rand(pricing.price_per_learner_month('quintile_3')),
        )
        self.assertFalse(result['needs_manual_school_type'])
        self.assertEqual(result['prefilled_learners'], pricing.minimum_learners())

    def test_directory_record_without_quantile_requests_manual_school_type(self):
        result = directory_result({
            'school_name': 'UNCLASSIFIED SCHOOL',
            'location': '',
            'quantile': '',
        }, 0)

        self.assertIsNone(result['price_school_type'])
        self.assertEqual(result['price_per_learner_month'], '')
        self.assertTrue(result['needs_manual_school_type'])

    def test_manual_school_options_are_named_as_quantiles(self):
        school_types = finder_context()['school_finder']['school_types']

        self.assertEqual(
            school_types[:5],
            [
                ('school_type_1', 'School quantile Q1'),
                ('school_type_2', 'School quantile Q2'),
                ('school_type_3', 'School quantile Q3'),
                ('school_type_4', 'School quantile Q4'),
                ('school_type_5', 'School quantile Q5'),
            ],
        )

    @patch('schools.views.search_school_directory', return_value=[])
    def test_brixx_is_empty_when_absent_from_the_shared_directory(self, search):
        status, payload = self.request_search('Brixx')

        self.assertEqual(status, 200)
        self.assertEqual(payload['count'], 0)
        search.assert_called_once_with('Brixx', limit=10)
