"""Search the national school directory shared by registration and Enterprise."""

import csv
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def school_directory_records():
    """Load the public school-name fields from the checked-in directory."""
    directory_path = (
        settings.BASE_DIR / 'static' / 'data' / 'national_schools.csv'
    )
    if not directory_path.is_file():
        return ()

    with directory_path.open(encoding='utf-8-sig', newline='') as directory_file:
        return tuple(
            {
                'school_name': row['school_name'].strip(),
                'location': (
                    ''
                    if row['location'].strip().upper()
                    in {'99', 'UNKNOWN', 'NULL', 'N/A'}
                    else row['location'].strip()
                ),
                'quantile': row['quantile'].strip(),
            }
            for row in csv.DictReader(directory_file)
            if row.get('school_name', '').strip()
        )


def search_school_records(query, records, limit=12):
    """Match names or locations using the teacher registration directory rules."""
    query = (query or '').strip()[:100].casefold()
    if len(query) < 2:
        return []

    matches = []
    for school in records:
        normalized_name = school['school_name'].casefold()
        normalized_location = school['location'].casefold()
        if query in normalized_name or query in normalized_location:
            name_rank = 0 if normalized_name.startswith(query) else 1
            matches.append((name_rank, school))

    matches.sort(
        key=lambda match: (
            match[0],
            match[1]['school_name'].casefold(),
            match[1]['location'].casefold(),
            match[1]['quantile'],
        )
    )
    return [school for _rank, school in matches[:limit]]


def search_school_directory(query, limit=12):
    """Search the shared national directory."""
    return search_school_records(query, school_directory_records(), limit)
