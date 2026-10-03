"""Template context for the shared school finder (see templates/includes/school_finder.html)."""

import json

from django.conf import settings
from django.utils.html import escape

from schools.resolution import NO_QUINTILE_MESSAGE, serialise
from schools.views import MAX_RESULTS, MIN_QUERY_LENGTH

FOOTNOTE = (
    "School quintiles are from the Department of Basic Education's National "
    'Master List of Schools and may be updated. Final pricing is confirmed on '
    'activation.'
)

NOT_FOUND_PROMPT = "Can't find your school? Select your school type manually"


def finder_context(
    instance='page',
    school=None,
    school_type_key='',
    learners=None,
    autofill_name=False,
):
    """
    Everything the finder partial needs. ``instance`` keeps the element ids unique
    when more than one finder appears on a page. ``school`` preselects a school,
    which is how a quote handed over from the pricing dialog arrives already
    filled in.
    """
    selected = serialise(school) if school is not None else None
    return {
        'school_finder': {
            'instance': instance,
            'provinces': settings.PROVINCES,
            'search_endpoint': '/api/schools/search/',
            'quote_endpoint': '/subscription/enterprise-pricing',
            'redeem_url': '/subscription/redeem-package',
            'minimum_learners': settings.MINIMUM_LEARNERS,
            'min_query_length': MIN_QUERY_LENGTH,
            'max_results': MAX_RESULTS,
            'school_types': settings.SCHOOL_TYPES,
            'no_quintile_message': NO_QUINTILE_MESSAGE,
            'not_found_prompt': NOT_FOUND_PROMPT,
            'footnote': FOOTNOTE,
            'autofill_name': autofill_name,
            # Preselection, when the user arrived from the pricing dialog. The
            # JSON goes into a data attribute, so it is escaped for HTML.
            'selected_school': selected,
            'selected_school_json': escape(
                json.dumps(selected) if selected is not None else ''
            ),
            'selected_school_type': school_type_key,
            'selected_learners': learners,
        },
    }