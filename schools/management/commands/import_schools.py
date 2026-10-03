"""
Load the DBE National Master List of Schools into the ``schools.School`` table.

    python manage.py import_schools
    python manage.py import_schools data/schools_master_list_clean.csv
    python manage.py import_schools "C:/path/to/master list.xlsx" --sheet Sheet1

Reads CSV with the standard library and XLSX with openpyxl, so a 25k-row import
needs no heavyweight dependency. Safe to re-run: schools are matched on EMIS
number and updated in place, so a newer master list refreshes the table rather
than duplicating it.

Only published school details are imported. Contact details, if the source file
carries them, are ignored and never stored.
"""

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from schools.models import School

QUINTILE_RANGE = range(1, 6)

SECTOR_MAP = {
    'public': 'public',
    'government': 'public',
    'government aided': 'public',
    'independent': 'independent',
    'private': 'independent',
}

STATUS_MAP = {
    'open': 'open',
    'pending open': 'pending open',
    'pending': 'pending open',
}

WRITABLE_FIELDS = [
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


def text(value):
    """Trimmed string, or '' for anything blank-ish (including None)."""
    if value is None:
        return ''
    return str(value).replace('\u00a0', ' ').strip()


def squash(value):
    """Trimmed with runs of whitespace collapsed, for spacing-insensitive matching."""
    return ' '.join(text(value).split())


def synthetic_emis(name, province):
    """
    A stable stand-in EMIS number for a row that has none, so the school is not
    lost from search and re-running still matches the same row. The ``X-`` prefix
    makes it obvious it did not come from the DBE.
    """
    digest = hashlib.sha1(
        f'{squash(name).lower()}|{province.lower()}'.encode('utf-8')
    ).hexdigest()[:14]
    return f'X-{digest}'


def clean_quintile(value):
    """
    A quintile of 1-5, or ``None``. The master list leaves it blank for schools
    it has not classified, and we never guess one.
    """
    raw = text(value)
    if not raw:
        return None
    digits = re.sub(r'[^0-9]', '', raw)
    if not digits:
        return None
    number = int(digits)
    return number if number in QUINTILE_RANGE else None


def clean_learners(value):
    raw = text(value).replace(' ', '')
    if not raw:
        return None
    match = re.match(r'^[0-9]+', raw)
    if not match:
        return None
    number = int(match.group(0))
    return number if number > 0 else None


def clean_province(value):
    """
    Map whatever the file calls a province onto one of the nine canonical names,
    matching loosely so "KZN", "KwaZulu Natal" and "KWAZULU-NATAL" all land on
    "KwaZulu-Natal".
    """
    raw = text(value)
    if not raw:
        return ''
    canonical = {province.lower(): province for province in settings.PROVINCES}
    key = squash(raw).lower()
    if key in canonical:
        return canonical[key]
    stripped = re.sub(r'\s+province$', '', key)
    if stripped in canonical:
        return canonical[stripped]
    squashed = stripped.replace('-', '').replace(' ', '')
    for lower, province in canonical.items():
        if lower.replace('-', '').replace(' ', '') == squashed:
            return province
    return settings.PROVINCE_ALIASES.get(key, '')


def clean_choice(value, mapping, default):
    raw = text(value).lower()
    if not raw:
        return default
    return mapping.get(raw, default)


def build_record(row):
    """
    Turn one source row into model kwargs, or return ``(None, reason)`` when the
    row is unusable. Never raises: a malformed row is skipped, not fatal.
    """
    name = squash(row.get('name'))
    if not name:
        return None, 'missing school name'

    province = clean_province(row.get('province'))
    if not province:
        return None, f'unrecognised province {text(row.get("province"))!r}'

    return {
        'emis_number': text(row.get('emis_number')),
        'name': text(row.get('name')),
        'province': province,
        'district': text(row.get('district')),
        'town': text(row.get('town')),
        'township_village': text(row.get('township_village')),
        # A blank or out-of-range quintile stays None: the UI asks the school
        # rather than us guessing which quintile it is.
        'quintile': clean_quintile(row.get('quintile')),
        'sector': clean_choice(row.get('sector'), SECTOR_MAP, 'unknown'),
        'status': clean_choice(row.get('status'), STATUS_MAP, 'open'),
        'school_type': text(row.get('school_type')),
        'urban_rural': text(row.get('urban_rural')),
        'learners_2025': clean_learners(row.get('learners_2025')),
    }, None


def read_csv_rows(path):
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        yield from csv.DictReader(handle)


def read_xlsx_rows(path, sheet=None):
    try:
        import openpyxl
    except ImportError as error:  # pragma: no cover - environment dependent
        raise CommandError(
            'Reading .xlsx needs openpyxl. Install it with: pip install openpyxl'
        ) from error

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook[sheet] if sheet else workbook.worksheets[0]
    try:
        rows = worksheet.iter_rows(values_only=True)
        header = [text(cell) for cell in next(rows)]
        for values in rows:
            yield dict(zip(header, values))
    finally:
        workbook.close()


class Command(BaseCommand):
    help = 'Import the DBE National Master List of Schools into the School table.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            nargs='?',
            default=str(settings.SCHOOLS_DATA_PATH),
            help='CSV or XLSX file to import. Defaults to SCHOOLS_DATA_PATH.',
        )
        parser.add_argument(
            '--sheet',
            default=None,
            help='Worksheet name for .xlsx files. Defaults to the first sheet.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Read and clean the file, report what would change, write nothing.',
        )

    def handle(self, *args, **options):
        path = Path(options['path']).expanduser()
        if not path.exists():
            raise CommandError(
                f'School list not found: {path}\n'
                'Download the DBE National Master List of Schools and save it to '
                f'{settings.SCHOOLS_DATA_PATH}, then re-run this command.'
            )

        suffix = path.suffix.lower()
        if suffix == '.csv':
            rows = read_csv_rows(path)
        elif suffix in ('.xlsx', '.xlsm'):
            rows = read_xlsx_rows(path, options['sheet'])
        else:
            raise CommandError(
                f'Unsupported file type {suffix!r}. Expected .csv or .xlsx.'
            )

        self.stdout.write(f'Reading {path}')
        dry_run = options['dry_run']

        stats = Counter()
        skipped = Counter()
        examples = {}
        records = {}

        for row in rows:
            stats['read'] += 1
            record, reason = build_record(row)
            if record is None:
                stats['skipped'] += 1
                skipped[reason] += 1
                examples.setdefault(reason, text(row.get('name')) or '<blank>')
                continue
            if not record['emis_number']:
                stats['synthetic_emis'] += 1
                record['emis_number'] = synthetic_emis(
                    record['name'], record['province']
                )
            # Later rows win, matching how a spreadsheet would read.
            records[record['emis_number']] = record

        stats['imported'] = len(records)

        created = updated = unchanged = 0
        if not dry_run:
            created, updated, unchanged = self._persist(records)
        stats['created'] = created
        stats['updated'] = updated
        stats['unchanged'] = unchanged

        self._report(stats, skipped, examples, dry_run)

    def _persist(self, records):
        """
        Insert new schools and update existing ones, keyed on EMIS number with a
        name+province fallback. Bulk operations because this runs over 25k rows.

        Only genuinely changed rows are written back: a re-import of an unchanged
        list (or one where only a few hundred schools moved) then costs a single
        read instead of tens of thousands of row updates.
        """
        incoming = list(records.values())
        existing = list(School.objects.all())
        by_emis = {school.emis_number: school for school in existing}
        by_name_province = {}
        for school in existing:
            key = (squash(school.name).lower(), school.province.lower())
            by_name_province.setdefault(key, school)

        to_create = []
        to_update = []
        unchanged = 0
        for record in incoming:
            school = by_emis.get(record['emis_number'])
            if school is None:
                school = by_name_province.get(
                    (squash(record['name']).lower(), record['province'].lower())
                )
            if school is None:
                to_create.append(School(**record))
                continue

            changed = False
            for field in WRITABLE_FIELDS:
                if getattr(school, field) != record[field]:
                    setattr(school, field, record[field])
                    changed = True
            if changed:
                to_update.append(school)
            else:
                unchanged += 1

        if to_create:
            School.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            School.objects.bulk_update(to_update, WRITABLE_FIELDS, batch_size=500)
        return len(to_create), len(to_update), unchanged

    def _report(self, stats, skipped, examples, dry_run):
        out = self.stdout.write
        out('')
        if dry_run:
            out(self.style.WARNING('DRY RUN - nothing written.'))
        out(f'Rows read          : {stats["read"]}')
        out(f'Schools imported   : {stats["imported"]}')
        out(f'Rows skipped       : {stats["skipped"]}')
        if stats['synthetic_emis']:
            out(f'Rows given a placeholder EMIS number: {stats["synthetic_emis"]}')
        for reason, count in skipped.most_common():
            sample = f'  e.g. {examples[reason]!r}' if reason in examples else ''
            out(f'      {count:>6}  {reason}{sample}')

        if dry_run:
            return

        out('')
        out(
            f'Created {stats["created"]}, updated {stats["updated"]}, '
            f'unchanged {stats["unchanged"]}'
        )
        self._breakdown()

    def _breakdown(self):
        out = self.stdout.write
        out('')
        out(f'Total schools in database: {School.objects.count()}')

        out('')
        out('By province:')
        for row in (
            School.objects.values('province')
            .annotate(n=Count('id'))
            .order_by('province')
        ):
            out(f'    {row["n"]:>6}  {row["province"]}')

        out('')
        out('By quintile:')
        for row in (
            School.objects.values('quintile')
            .annotate(n=Count('id'))
            .order_by('quintile')
        ):
            label = f'Quintile {row["quintile"]}' if row['quintile'] else 'No quintile'
            out(f'    {row["n"]:>6}  {label}')