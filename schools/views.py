"""Public JSON search over the DBE school list, for the Enterprise school finder."""

from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from schools.models import School
from schools.resolution import serialise

# A province plus three characters is enough to be useful without letting the
# endpoint return the whole country on every keystroke.
MIN_QUERY_LENGTH = 3
MAX_RESULTS = 10
SEARCHABLE_STATUS = 'open'


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


def normalise_province(raw):
    """Accept the canonical province name, case- and spacing-insensitively."""
    wanted = ' '.join((raw or '').split()).lower()
    for province in settings.PROVINCES:
        if province.lower() == wanted:
            return province
    return ''


def normalise_query(raw):
    """Collapse extra spaces so "  ntuz  " matches "NTUZUMA"."""
    return ' '.join((raw or '').split())


def find_schools(province, query):
    """
    Open schools in one province whose name matches, best match first.

    The province filter uses the (province, status) index, which narrows 25,000
    schools to roughly 2,800 before any name matching happens, so the three-tier
    ordering below stays cheap.
    """
    lowered = query.lower()
    return list(
        School.objects.filter(province=province, status=SEARCHABLE_STATUS)
        .filter(name__icontains=query)
        .annotate(
            match_rank=Case(
                When(name__iexact=query, then=Value(0)),
                When(name__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by('match_rank', 'name', 'emis_number')[:MAX_RESULTS]
    )


@require_http_methods(['GET'])
def school_search(request):
    """
    GET /api/schools/search/?province=Free State&q=ntuz

    Returns up to ten open schools, each with the quintile, sector, published
    enrolment and the Enterprise price per learner per month for the active
    PRICING_MODE. Prices come from ``schools.resolution`` -> ``lessons.pricing``;
    none are stored here.
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

    province = normalise_province(request.GET.get('province'))
    query = normalise_query(request.GET.get('q'))

    if not province:
        return JsonResponse(
            {
                'error': 'Choose a province before searching for your school.',
                'code': 'province_required',
                'provinces': settings.PROVINCES,
            },
            status=400,
        )

    if len(query) < MIN_QUERY_LENGTH:
        return JsonResponse(
            {
                'error': (
                    f'Type at least {MIN_QUERY_LENGTH} letters of your school name.'
                ),
                'code': 'query_too_short',
            },
            status=400,
        )

    schools = find_schools(province, query)

    return JsonResponse(
        {
            'province': province,
            'query': query,
            'count': len(schools),
            'pricing_mode': settings.PRICING_MODE,
            'minimum_learners': settings.MINIMUM_LEARNERS,
            'results': [serialise(school) for school in schools],
        }
    )