"""Public JSON search over the DBE school list, for the Enterprise school finder."""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from lessons.pricing import (
    format_rand,
    minimum_learners,
    price_per_learner_month,
)
from schools.directory import search_school_directory

# Keep the minimum aligned with teacher registration's national-directory search.
MIN_QUERY_LENGTH = 2
MAX_RESULTS = 10


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request):
    """
    Fixed-window per-IP throttle using the cache. Deliberately simple: the goal is
    to stop casual scraping, not to run a distributed rate limiter.
    """
    limit = settings.SCHOOLS_SEARCH_RATE_LIMIT
    if not limit:
        return False
    window = settings.SCHOOLS_SEARCH_RATE_WINDOW
    key = f'schools-search:{client_ip(request)}'

    used = cache.get(key)
    if used is None:
        cache.set(key, 1, window)
        return False
    if used >= limit:
        return True
    try:
        cache.incr(key)
    except ValueError:  # window expired between get and incr
        cache.set(key, 1, window)
    return False


def normalise_query(raw):
    """Collapse extra spaces before the shared directory matcher sees the query."""
    return ' '.join((raw or '').split())[:100]


def directory_result(record, index):
    """Adapt the teacher directory record to the Enterprise finder response."""
    quantile = record['quantile'].strip().upper()
    number = int(quantile[1]) if (
        len(quantile) == 2 and quantile[0] == 'Q' and quantile[1] in '12345'
    ) else None
    school_type = f'quintile_{number}' if number else None
    minimum = minimum_learners()
    location = record['location']
    name = record['school_name']
    place = f', {location}' if location else ''
    return {
        'id': f'directory-{index}',
        'emis_number': '',
        'name': name,
        'display_label': f'{name}{place}',
        'province': '',
        'district': '',
        'town': location,
        'township_village': '',
        'quintile': number,
        'sector': 'unknown',
        'school_type_label': f'Quantile {number}' if number else '',
        'learners_2025': None,
        'price_school_type': school_type,
        'price_per_learner_month': (
            format_rand(price_per_learner_month(school_type))
            if school_type else ''
        ),
        'needs_manual_school_type': school_type is None,
        'school_type_note': (
            f'Directory quantile {quantile}; pricing uses school type {number}.'
            if number else
            "We don't have a school type on record for this school. "
            'Please select it below.'
        ),
        'minimum_learners': minimum,
        'prefilled_learners': minimum,
    }


@require_http_methods(['GET'])
def school_search(request):
    """
    GET /api/schools/search/?q=ntuz

    Returns up to ten matching schools from the same national directory used by
    teacher registration, with any available quantile mapped to Enterprise pricing.
    The source has no province or enrolment fields, so neither is inferred here.
    """
    if is_rate_limited(request):
        return JsonResponse(
            {
                'error': 'Too many searches. Please wait a moment and try again.',
                'code': 'rate_limited',
            },
            status=429,
            headers={'Retry-After': str(settings.SCHOOLS_SEARCH_RATE_WINDOW)},
        )

    query = normalise_query(request.GET.get('q'))

    if len(query) < MIN_QUERY_LENGTH:
        return JsonResponse({
            'query': query,
            'count': 0,
            'pricing_mode': settings.PRICING_MODE,
            'minimum_learners': settings.MINIMUM_LEARNERS,
            'results': [],
        })

    records = search_school_directory(query, limit=MAX_RESULTS)
    schools = [
        directory_result(record, index)
        for index, record in enumerate(records)
    ]

    return JsonResponse(
        {
            'query': query,
            'count': len(schools),
            'pricing_mode': settings.PRICING_MODE,
            'minimum_learners': settings.MINIMUM_LEARNERS,
            'results': schools,
        }
    )