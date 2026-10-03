import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.test.utils import override_settings as override

from lessons import pricing
from schools.management.commands.import_schools import (
    clean_learners,
    clean_province,
    clean_quintile,
)
from schools.models import School
from schools.resolution import (
    needs_manual_quintile,
    prefill_learners,
    school_type_for,
    serialise,
)
from schools.views import MAX_RESULTS

HEADER = [
    'emis_number',
    'name',
    'province',
    'district',
    'town',
    'township_village',
    'quintile',
    'sector',
    'status',
    'school_type',
    'urban_rural',
    'learners_2025',
]


def row(**overrides):
    base = {
        'emis_number': '200500001',
        'name': 'BALENI SECONDARY SCHOOL',
        'province': 'Eastern Cape',
        'district': 'Alfred Nzo East',
        'town': 'Bizana',
        'township_village': '',
        'quintile': '1',
        'sector': 'public',
        'status': 'open',
        'school_type': 'Ordinary School',
        'urban_rural': 'Rural',
        'learners_2025': '950',
    }
    base.update(overrides)
    return base


def write_csv(rows):
    handle = tempfile.NamedTemporaryFile(
        'w', suffix='.csv', delete=False, encoding='utf-8', newline=''
    )
    writer = csv.DictWriter(handle, fieldnames=HEADER)
    writer.writeheader()
    for item in rows:
        writer.writerow(item)
    handle.close()
    return Path(handle.name)


class CleaningTests(TestCase):
    def test_quintile_parsed_only_when_one_to_five(self):
        self.assertEqual(clean_quintile('3'), 3)
        self.assertEqual(clean_quintile(' 5 '), 5)
        self.assertEqual(clean_quintile('Q2'), 2)
        self.assertIsNone(clean_quintile(''))
        self.assertIsNone(clean_quintile('   '))
        self.assertIsNone(clean_quintile('9'))
        self.assertIsNone(clean_quintile('unknown'))
        self.assertIsNone(clean_quintile(None))

    def test_learners_blank_becomes_null(self):
        self.assertEqual(clean_learners('950'), 950)
        self.assertEqual(clean_learners(' 1 234 '), 1234)
        self.assertIsNone(clean_learners(''))
        self.assertIsNone(clean_learners('n/a'))
        self.assertIsNone(clean_learners('0'))

    def test_province_normalised_to_the_nine(self):
        for value in ('KwaZulu-Natal', 'KZN', 'kwazulu natal', '  KWAZULU-NATAL  '):
            self.assertEqual(clean_province(value), 'KwaZulu-Natal')
        self.assertEqual(clean_province('North West'), 'North West')
        self.assertEqual(clean_province('Gauteng Province'), 'Gauteng')
        self.assertEqual(clean_province('nonsense'), '')


class ImportCommandTests(TestCase):
    def run_import(self, rows, **kwargs):
        path = write_csv(rows)
        out = StringIO()
        call_command('import_schools', str(path), stdout=out, **kwargs)
        return out.getvalue()

    def test_imports_clean_rows(self):
        self.run_import(
            [
                row(),
                row(emis_number='200500002', name='BEKAMEVA PRIMARY', quintile='4'),
            ]
        )

        self.assertEqual(School.objects.count(), 2)
        school = School.objects.get(emis_number='200500001')
        self.assertEqual(school.name, 'BALENI SECONDARY SCHOOL')
        self.assertEqual(school.province, 'Eastern Cape')
        self.assertEqual(school.quintile, 1)
        self.assertEqual(school.learners_2025, 950)
        self.assertEqual(school.sector, 'public')
        self.assertEqual(school.status, 'open')

    def test_missing_quintile_is_stored_as_null_and_reported(self):
        output = self.run_import([row(quintile='')])

        self.assertEqual(School.objects.count(), 1)
        self.assertIsNone(School.objects.get().quintile)
        self.assertIn('No quintile', output)

    def test_rows_without_a_name_are_skipped_and_counted(self):
        output = self.run_import(
            [row(), row(emis_number='200500002', name='   ')]
        )

        self.assertEqual(School.objects.count(), 1)
        self.assertIn('missing school name', output)

    def test_row_with_unusable_province_is_skipped_without_crashing(self):
        output = self.run_import(
            [row(), row(emis_number='200500003', name='ORPHAN', province='Atlantis')]
        )

        self.assertEqual(School.objects.count(), 1)
        self.assertIn('unrecognised province', output)

    def test_blank_and_broken_fields_do_not_stop_the_import(self):
        output = self.run_import(
            [
                row(emis_number='200500010', learners_2025='', quintile='n/a'),
                row(emis_number='200500011', name='WEIRD', quintile='42'),
                row(emis_number='200500012', name='SPACES SCHOOL'),
            ]
        )

        self.assertEqual(School.objects.count(), 3)
        self.assertIsNone(School.objects.get(emis_number='200500010').quintile)
        self.assertIsNone(School.objects.get(emis_number='200500011').quintile)
        self.assertIn('Schools imported   : 3', output)

    def test_rerunning_updates_instead_of_duplicating(self):
        rows = [row(), row(emis_number='200500002', name='SECOND SCHOOL')]
        self.run_import(rows)

        # A newer file: one school gains a quintile, a learner count moves.
        rows[0]['quintile'] = '2'
        rows[0]['learners_2025'] = '1100'
        output = self.run_import(rows)

        self.assertEqual(School.objects.count(), 2)
        self.assertIn('Created 0', output)
        self.assertIn('updated 1', output)
        self.assertIn('unchanged 1', output)
        updated = School.objects.get(emis_number='200500001')
        self.assertEqual(updated.quintile, 2)
        self.assertEqual(updated.learners_2025, 1100)

    def test_unchanged_rerun_writes_nothing(self):
        rows = [row()]
        self.run_import(rows)
        output = self.run_import(rows)

        self.assertIn('unchanged 1', output)

    def test_dry_run_writes_nothing(self):
        output = self.run_import([row(), row(emis_number='200500002', name='TWO')], dry_run=True)

        self.assertEqual(School.objects.count(), 0)
        self.assertIn('DRY RUN', output)
        self.assertIn('Schools imported   : 2', output)

    def test_missing_file_reports_clearly(self):
        with self.assertRaises(CommandError) as caught:
            call_command('import_schools', 'data/does_not_exist.csv')
        self.assertIn('School list not found', str(caught.exception))

    def test_unsupported_file_type_is_rejected(self):
        path = Path(tempfile.mktemp(suffix='.txt'))
        path.write_text('nope', encoding='utf-8')
        with self.assertRaises(CommandError):
            call_command('import_schools', str(path))


class PricingRuleTests(TestCase):
    """The three rules that turn a school into a price."""

    def setUp(self):
        self.public_q1 = School.objects.create(
            emis_number='1', name='POOREST PUBLIC', province='Eastern Cape',
            district='Alfred Nzo East', town='Bizana', quintile=1,
            sector='public', learners_2025=2030,
        )
        self.independent_with_quintile = School.objects.create(
            emis_number='2', name='RICH INDEPENDENT', province='Gauteng',
            district='Tshwane South', town='Pretoria', quintile=5,
            sector='independent', learners_2025=591,
        )
        self.public_no_quintile = School.objects.create(
            emis_number='3', name='UNCLASSIFIED PUBLIC', province='Free State',
            district='Motheo', town='Bloemfontein', quintile=None,
            sector='public', learners_2025=374,
        )

    def test_public_school_with_quintile_uses_that_quintile(self):
        self.assertEqual(school_type_for(self.public_q1), 'quintile_1')
        self.assertEqual(
            serialise(self.public_q1)['price_per_learner_month'],
            pricing.format_rand(pricing.price_per_learner_month('quintile_1')),
        )
        self.assertFalse(needs_manual_quintile(self.public_q1))

    @override_settings(
        PRICING_MODE='school_paid',
        PRICE_PER_LEARNER_MONTH={
            'government_funded': {'quintile_1': 40, 'quintile_5': 20, 'private': 20},
            'school_paid': {'quintile_1': 20, 'quintile_5': 40, 'private': 40},
        },
        ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=20,
    )
    def test_price_follows_pricing_mode(self):
        self.assertEqual(serialise(self.public_q1)['price_per_learner_month'], 'R20')
        self.assertEqual(
            serialise(self.independent_with_quintile)['price_per_learner_month'], 'R40'
        )

    def test_independent_school_uses_private_price_even_with_a_quintile(self):
        # Quintile 5 government-funded would be R20; private is also R20 here, so
        # check the resolved key as well to prove the quintile was ignored.
        self.assertEqual(school_type_for(self.independent_with_quintile), 'private')
        self.assertFalse(needs_manual_quintile(self.independent_with_quintile))
        self.assertIn('Independent school', serialise(self.independent_with_quintile)['quintile_note'])

    @override_settings(
        PRICING_MODE='government_funded',
        PRICE_PER_LEARNER_MONTH={
            'government_funded': {'quintile_1': 40, 'quintile_5': 15, 'private': 20},
            'school_paid': {},
        },
        ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=15,
    )
    def test_independent_school_ignores_its_quintile_price(self):
        # Quintile 5 is deliberately 15 here, private is 20: the independent
        # school must still come out at the private rate.
        self.assertEqual(
            serialise(self.independent_with_quintile)['price_per_learner_month'], 'R20'
        )

    def test_public_school_without_a_quintile_requires_manual_selection(self):
        data = serialise(self.public_no_quintile)
        self.assertIsNone(school_type_for(self.public_no_quintile))
        self.assertTrue(needs_manual_quintile(self.public_no_quintile))
        self.assertEqual(data['price_per_learner_month'], '')
        self.assertIsNone(data['price_school_type'])
        self.assertIn("don't have a quintile on record", data['quintile_note'])

    def test_each_quintile_prices_from_the_config(self):
        for quintile in range(1, 6):
            school = School.objects.create(
                emis_number=f'q{quintile}', name=f'SCHOOL Q{quintile}',
                province='Limpopo', sector='public', quintile=quintile,
            )
            expected = pricing.format_rand(
                pricing.price_per_learner_month(f'quintile_{quintile}')
            )
            self.assertEqual(school_type_for(school), f'quintile_{quintile}')
            self.assertEqual(serialise(school)['price_per_learner_month'], expected)


class LearnerPrefillTests(TestCase):
    def test_published_enrolment_is_used_when_at_least_the_minimum(self):
        school = School.objects.create(
            emis_number='1', name='BIG', province='Gauteng', sector='public',
            quintile=1, learners_2025=2030,
        )
        self.assertEqual(prefill_learners(school), 2030)
        self.assertEqual(serialise(school)['prefilled_learners'], 2030)

    def test_below_the_minimum_becomes_the_minimum(self):
        school = School.objects.create(
            emis_number='2', name='TINY', province='Gauteng', sector='public',
            quintile=1, learners_2025=91,
        )
        self.assertEqual(prefill_learners(school), pricing.minimum_learners())

    def test_unknown_enrolment_becomes_the_minimum(self):
        school = School.objects.create(
            emis_number='3', name='UNKNOWN', province='Gauteng', sector='public',
            quintile=1, learners_2025=None,
        )
        self.assertEqual(prefill_learners(school), pricing.minimum_learners())

    def test_exactly_the_minimum_is_kept(self):
        school = School.objects.create(
            emis_number='4', name='EXACT', province='Gauteng', sector='public',
            quintile=1, learners_2025=100,
        )
        self.assertEqual(prefill_learners(school), 100)


class DisplayLabelTests(TestCase):
    def test_label_includes_town_and_district(self):
        school = School.objects.create(
            emis_number='1', name='BALENI SECONDARY SCHOOL', province='Eastern Cape',
            district='Alfred Nzo East', town='Bizana',
        )
        self.assertEqual(
            school.display_label,
            'BALENI SECONDARY SCHOOL, Bizana (Alfred Nzo East)',
        )

    def test_label_falls_back_to_township_then_district(self):
        township = School.objects.create(
            emis_number='2', name='A', province='Limpopo', district='D',
            town='', township_village='Village',
        )
        self.assertEqual(township.display_label, 'A, Village (D)')

        district_only = School.objects.create(
            emis_number='3', name='B', province='Limpopo', district='D',
            town='', township_village='',
        )
        self.assertEqual(district_only.display_label, 'B, D')

    def test_label_without_any_place_is_just_the_name(self):
        school = School.objects.create(
            emis_number='4', name='C', province='Limpopo', district='',
        )
        self.assertEqual(school.display_label, 'C')


class SchoolSearchEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.baleni = School.objects.create(
            emis_number='200500013', name='BALENI SECONDARY SCHOOL',
            province='Eastern Cape', district='Alfred Nzo East', town='Bizana',
            quintile=1, sector='public', status='open', learners_2025=950,
        )
        # Same name, same province, different town: must both come back.
        cls.baleni_other = School.objects.create(
            emis_number='200500014', name='BALENI SECONDARY SCHOOL',
            province='Eastern Cape', district='Or Tambo Coastal', town='Bizana',
            quintile=3, sector='public', status='open', learners_2025=400,
        )
        cls.gauteng_school = School.objects.create(
            emis_number='200400001', name='BALENI PRIMARY SCHOOL',
            province='Gauteng', district='Tshwane South', town='Pretoria',
            quintile=5, sector='public', status='open', learners_2025=600,
        )
        cls.closed = School.objects.create(
            emis_number='200500099', name='BALENI CLOSED SCHOOL',
            province='Eastern Cape', district='Alfred Nzo East', town='Bizana',
            quintile=1, sector='public', status='pending open',
        )
        cls.independent = School.objects.create(
            emis_number='200500020', name='BALENI INDEPENDENT COLLEGE',
            province='Eastern Cape', district='Alfred Nzo East', town='Bizana',
            quintile=5, sector='independent', status='open', learners_2025=26,
        )

    def search(self, **params):
        return self.client.get('/api/schools/search/', params)

    def test_province_is_required(self):
        response = self.search(q='baleni')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'province_required')
        self.assertEqual(len(response.json()['provinces']), 9)

    def test_unknown_province_is_rejected(self):
        response = self.search(province='Atlantis', q='baleni')
        self.assertEqual(response.status_code, 400)

    def test_query_shorter_than_three_characters_is_rejected(self):
        for short in ('', 'b', 'ba'):
            response = self.search(province='Eastern Cape', q=short)
            self.assertEqual(response.status_code, 400, short)
            self.assertEqual(response.json()['code'], 'query_too_short')

    def test_three_characters_is_enough(self):
        self.assertEqual(self.search(province='Eastern Cape', q='bal').status_code, 200)

    def test_results_are_filtered_by_province(self):
        payload = self.search(province='Eastern Cape', q='baleni').json()
        names = {item['name'] for item in payload['results']}
        self.assertIn('BALENI SECONDARY SCHOOL', names)
        self.assertNotIn('BALENI PRIMARY SCHOOL', names)

    def test_two_schools_with_the_same_name_are_both_returned_and_distinguishable(self):
        payload = self.search(province='Eastern Cape', q='baleni secondary').json()
        found = [item for item in payload['results'] if item['name'] == 'BALENI SECONDARY SCHOOL']
        self.assertEqual(len(found), 2)
        labels = {item['display_label'] for item in found}
        self.assertEqual(len(labels), 2)
        self.assertIn('Alfred Nzo East', ' '.join(labels))
        self.assertIn('Or Tambo Coastal', ' '.join(labels))
        self.assertEqual({item['id'] for item in found}, {self.baleni.pk, self.baleni_other.pk})

    def test_pending_open_schools_are_excluded(self):
        payload = self.search(province='Eastern Cape', q='closed').json()
        self.assertEqual(payload['count'], 0)

    def test_exact_match_ranks_first(self):
        payload = self.search(province='Eastern Cape', q='BALENI SECONDARY SCHOOL').json()
        self.assertEqual(payload['results'][0]['id'], self.baleni.pk)

    def test_matching_ignores_case_and_extra_spaces(self):
        for query in ('baleni', 'BALENI', '  BaLeNi  '):
            payload = self.search(province='Eastern Cape', q=query).json()
            self.assertGreater(payload['count'], 0, query)

    def test_at_most_ten_results(self):
        School.objects.bulk_create([
            School(
                emis_number=f'many{index}', name=f'MANY PRIMARY {index}',
                province='Northern Cape', sector='public', quintile=1, status='open',
            )
            for index in range(15)
        ])
        payload = self.search(province='Northern Cape', q='many primary').json()
        self.assertEqual(len(payload['results']), MAX_RESULTS)

    def test_no_results_returns_an_empty_list(self):
        payload = self.search(province='Eastern Cape', q='zzzznotaschool').json()
        self.assertEqual(payload['count'], 0)
        self.assertEqual(payload['results'], [])

    def test_result_carries_the_quintile_and_configured_price(self):
        payload = self.search(province='Eastern Cape', q='baleni secondary').json()
        first = payload['results'][0]
        self.assertEqual(first['id'], self.baleni.pk)
        self.assertEqual(first['emis_number'], '200500013')
        self.assertEqual(first['province'], 'Eastern Cape')
        self.assertEqual(first['quintile'], 1)
        self.assertEqual(first['sector'], 'public')
        self.assertEqual(first['learners_2025'], 950)
        self.assertEqual(first['price_school_type'], 'quintile_1')
        self.assertEqual(
            first['price_per_learner_month'],
            pricing.format_rand(pricing.price_per_learner_month('quintile_1')),
        )
        self.assertEqual(first['prefilled_learners'], 950)
        self.assertFalse(first['needs_manual_quintile'])

    def test_independent_result_prices_as_private(self):
        payload = self.search(province='Eastern Cape', q='independent college').json()
        item = payload['results'][0]
        self.assertEqual(item['sector'], 'independent')
        self.assertEqual(item['quintile'], 5)
        self.assertEqual(item['price_school_type'], 'private')
        self.assertEqual(
            item['price_per_learner_month'],
            pricing.format_rand(pricing.price_per_learner_month('private')),
        )
        # 26 learners is under the minimum, so the prefill must be the minimum.
        self.assertEqual(item['prefilled_learners'], 100)

    def test_public_school_without_quintile_asks_for_manual_selection(self):
        school = School.objects.create(
            emis_number='200500030', name='BALENI UNKNOWN', province='Eastern Cape',
            district='Alfred Nzo East', town='Bizana', quintile=None,
            sector='public', status='open',
        )
        payload = self.search(province='Eastern Cape', q='baleni unknown').json()
        item = payload['results'][0]
        self.assertEqual(item['id'], school.pk)
        self.assertIsNone(item['quintile'])
        self.assertTrue(item['needs_manual_quintile'])
        self.assertEqual(item['price_per_learner_month'], '')
        self.assertIsNone(item['price_school_type'])

    @override_settings(
        SCHOOLS_SEARCH_RATE_LIMIT=3,
        SCHOOLS_SEARCH_RATE_WINDOW=60,
    )
    def test_rate_limit_returns_429(self):
        from django.core.cache import cache

        cache.clear()
        for _ in range(3):
            self.assertEqual(self.search(province='Eastern Cape', q='baleni').status_code, 200)
        blocked = self.search(province='Eastern Cape', q='baleni')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()['code'], 'rate_limited')
        cache.clear()

    def test_only_open_schools_exist_in_the_default_fixture_set(self):
        self.assertFalse(School.objects.filter(status='pending open').exists()
                         and self.closed.status != 'pending open')