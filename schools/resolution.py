"""
Turning a school record into an Enterprise price.

This module owns the *rule* that connects a school to a price; it never owns a
price. Every amount comes from :mod:`lessons.pricing`, which reads the settings
pricing block, so changing ``PRICING_MODE`` or any number in it changes the
school finder with no edits here.

The rules, in order:

1. ``sector == 'independent'``  -> the Private/independent price, whatever
   quintile the master list happens to record for that school.
2. ``sector == 'public'`` with a quintile -> that quintile's price.
3. ``sector == 'public'`` with no quintile -> nothing. We do not guess; the UI
   asks the school to choose its own quintile.
"""

from lessons.pricing import (
    format_rand,
    minimum_learners,
    price_per_learner_month,
)

PRIVATE_SCHOOL_TYPE = 'private'

# Shown when rule 3 applies, so the school knows why it has to choose.
NO_QUINTILE_MESSAGE = (
    "We don't have a quintile on record for this school. "
    "Please select it below."
)

CONFIRM_ON_ACTIVATION_NOTE = (
    'The price will be confirmed on activation.'
)


def school_type_for(school):
    """
    The ``lessons.pricing`` school-type key for this school, or ``None`` when
    the caller has to ask (public school with no quintile on record).
    """
    if school.sector == 'independent':
        return PRIVATE_SCHOOL_TYPE
    if school.sector == 'public' and school.quintile:
        return f'quintile_{school.quintile}'
    return None


def price_for_school(school):
    """Formatted rand-per-learner-per-month, or ``''`` when it must be chosen."""
    school_type = school_type_for(school)
    if school_type is None:
        return ''
    return format_rand(price_per_learner_month(school_type))


def needs_manual_quintile(school):
    """True when we must not guess: a public school with no quintile on record."""
    return school_type_for(school) is None


def quintile_note(school):
    """One line explaining where this school's price came from."""
    if school.sector == 'independent':
        return (
            'Independent school, so this is our Private/independent rate.'
        )
    if school.sector == 'public' and school.quintile:
        return (
            f'Quintile {school.quintile} public school. Quintiles are the '
            "Department of Basic Education's poverty ranking — Quintile 1 is "
            'the poorest, Quintile 5 the least poor.'
        )
    return NO_QUINTILE_MESSAGE


def prefill_learners(school):
    """
    Start the learner count at the school's published enrolment, but never below
    the Enterprise minimum.
    """
    minimum = minimum_learners()
    published = school.learners_2025
    if published and published >= minimum:
        return published
    return minimum


def serialise(school):
    """
    The search-API shape for one school: identity and place, plus everything the
    browser needs to render the price and hand the selection to the activation
    flow.
    """
    school_type = school_type_for(school)
    return {
        'id': school.pk,
        'emis_number': school.emis_number,
        'name': school.name,
        'display_label': school.display_label,
        'province': school.province,
        'district': school.district,
        'town': school.town,
        'township_village': school.township_village,
        'quintile': school.quintile,
        'sector': school.sector,
        'school_type_label': school.school_type,
        'learners_2025': school.learners_2025,
        # The pricing inputs and outputs. `school_type` feeds the existing
        # quote endpoint, which does the actual arithmetic.
        'price_school_type': school_type,
        'price_per_learner_month': price_for_school(school),
        'needs_manual_quintile': needs_manual_quintile(school),
        'quintile_note': quintile_note(school),
        'minimum_learners': minimum_learners(),
        'prefilled_learners': prefill_learners(school),
    }