"""
Plan pricing for every plan SGILA sells.

Enterprise (school) pricing comes from the settings block
``SCHOOL_TYPES / MINIMUM_LEARNERS / PRICING_MODE / PRICE_PER_LEARNER_MONTH /
ANNUAL_PREPAY_MONTHS_BILLED`` — see ``sgila_project/settings.py``. The two
flat card-paid plans come from ``SUBSCRIPTION_PRICES`` in the same file. This
module is the *only* place that does arithmetic on those numbers, and the
*only* place that turns them into a currency string, so the plan cards, the
Enterprise pricing dialog and the JSON quote endpoint can never drift apart.

The dialog's live calculator does not re-implement any of this: it asks
``/subscription/enterprise-pricing`` for a quote and renders the strings that
come back. Prices are never hard-coded in a template or in JavaScript.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

MONTHS_PER_YEAR = 12


def _r(value):
    """Coerce config values to Decimal so money maths is exact."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _round2(value):
    return _r(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def format_rand(amount):
    """
    Render an amount as South African Rand: ``R1,234`` when it is a whole
    number of rand, ``R1,234.50`` when it is not. Grouping uses a comma as the
    thousands separator, which is the convention in South Africa.
    """
    value = _round2(_r(amount))
    quantised = f'{value:.2f}'
    whole, _, cents = quantised.partition('.')
    sign = ''
    if whole.startswith('-'):
        sign, whole = '-', whole[1:]
    grouped = f'{int(whole):,}'
    if cents.strip('0'):
        return f'{sign}R{grouped}.{cents}'
    return f'{sign}R{grouped}'


def plan_price(plan_type):
    """Rand per month for one of the flat card-paid plans."""
    return _round2(settings.SUBSCRIPTION_PRICES[plan_type])


def plan_prices():
    """
    The flat monthly price of each card-paid plan, already formatted:
    ``{'individual': 'R49', 'family': 'R89'}``.

    Enterprise is not here — it is priced per learner from the school-quintile
    table and reaches the cards through :func:`card_context`.
    """
    return {
        plan_type: format_rand(amount)
        for plan_type, amount in settings.SUBSCRIPTION_PRICES.items()
    }


def pricing_mode():
    return settings.PRICING_MODE


def minimum_learners():
    return int(settings.MINIMUM_LEARNERS)


def school_types():
    """``[{'value': 'quintile_1', 'label': 'Quintile 1 (poorest)'}, ...]``."""
    return [{'value': value, 'label': label} for value, label in settings.SCHOOL_TYPES]


def school_type_label(value):
    for entry in settings.SCHOOL_TYPES:
        if entry[0] == value:
            return entry[1]
    return ''


def is_valid_school_type(value):
    return any(entry[0] == value for entry in settings.SCHOOL_TYPES)


def active_price_table():
    """The per-learner monthly prices for the active ``PRICING_MODE``."""
    return settings.PRICE_PER_LEARNER_MONTH[settings.PRICING_MODE]


def price_per_learner_month(school_type):
    """Rand per learner per month for one school type."""
    return _round2(active_price_table()[school_type])


def start_price_per_learner_month():
    """
    The lowest price in the active mode's table — the "From R../month per
    learner" figure advertised on the Enterprise card.
    """
    return _round2(settings.ENTERPRISE_START_PRICE_PER_LEARNER_MONTH)


def annual_prepay_months_billed():
    """
    Months actually charged when paying a year up front, or ``None`` when the
    optional annual prepay discount is off.
    """
    months = getattr(settings, 'ANNUAL_PREPAY_MONTHS_BILLED', None)
    if months in (None, '', False):
        return None
    months = int(months)
    return months if 0 < months <= MONTHS_PER_YEAR else None


def show_funding_explainer():
    """
    Only the government-funded model needs the note about lower-quintile schools
    receiving more state funding and therefore paying more per learner.
    """
    return settings.PRICING_MODE == 'government_funded'


def parse_learners(raw):
    """
    Turn user input into a learner count. ``None`` means the field was blank
    or unusable; ``'error'`` is never returned — callers distinguish via
    :func:`normalise_learners`.
    """
    if raw is None:
        return None
    text = str(raw).strip().replace(',', '').replace(' ', '')
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def learners_error(learners):
    """Friendly validation message for a bad learner count, or ``''`` if fine."""
    minimum = minimum_learners()
    if learners is None:
        return 'Please enter how many learners your school needs.'
    if learners < minimum:
        return f'Enterprise packages start at {minimum} learners — please enter {minimum} or more.'
    return ''


def quote(school_type, learners):
    """
    The full Enterprise price calculation for one school type and learner
    count, with every figure already rounded and formatted for display.

    ``valid`` is ``False`` (and the money fields are ``None``) when the school
    type is unknown or the learner count is below the minimum, so the caller
    can show :attr:`error` instead of a number.
    """
    result = {
        'school_type': school_type,
        'school_type_label': school_type_label(school_type),
        'learners': learners,
        'minimum_learners': minimum_learners(),
        'pricing_mode': pricing_mode(),
        'valid': False,
        'error': '',
        'per_learner_month': None,
        'total_month': None,
        'total_year': None,
        'breakdown': '',
        'annual_prepay': None,
    }

    if not is_valid_school_type(school_type):
        result['error'] = 'Please choose your school type.'
        return result

    error = learners_error(learners)
    if error:
        result['error'] = error
        return result

    per_learner = price_per_learner_month(school_type)
    total_month = _round2(per_learner * _r(learners))
    total_year = _round2(total_month * _r(MONTHS_PER_YEAR))

    result.update({
        'valid': True,
        'per_learner_month': format_rand(per_learner),
        'total_month': format_rand(total_month),
        'total_year': format_rand(total_year),
        'breakdown': f'{learners:,} learners x {format_rand(per_learner)} = {format_rand(total_month)}/month',
    })

    prepay_months = annual_prepay_months_billed()
    if prepay_months is not None:
        total_prepay = _round2(per_learner * _r(learners) * _r(prepay_months))
        result['annual_prepay'] = {
            'months_billed': prepay_months,
            'months_free': MONTHS_PER_YEAR - prepay_months,
            'total': format_rand(total_prepay),
            'note': (
                f'Pay {format_rand(total_prepay)} up front for 12 months '
                f'({prepay_months} months charged, '
                f'{MONTHS_PER_YEAR - prepay_months} free).'
            ),
        }

    return result


def comparison_rows(learners=None):
    """
    One row per school type: its per-learner monthly price and what that costs
    for the minimum learner count, so schools can compare. Defaults to the
    minimum learner count when no count is supplied.
    """
    count = minimum_learners() if learners is None else learners
    count = max(count, minimum_learners())
    rows = []
    for entry in settings.SCHOOL_TYPES:
        value = entry[0]
        per_learner = price_per_learner_month(value)
        rows.append({
            'value': value,
            'label': entry[1],
            'per_learner_month': format_rand(per_learner),
            'minimum_total_month': format_rand(_round2(per_learner * _r(count))),
        })
    return rows


def card_context():
    """
    Everything the Enterprise card needs on ``/subscription``: the advertised
    "From R../month per learner" figure, its label and the minimum learner
    count, all read from config.
    """
    minimum = minimum_learners()
    return {
        'enterprise_start_price': format_rand(start_price_per_learner_month()),
        'enterprise_minimum_learners': minimum,
        'enterprise_minimum_learners_display': f'{minimum:,}',
        'enterprise_pricing_mode': pricing_mode(),
    }


def modal_context():
    """
    Everything the pricing dialog needs, including the initial quote for the
    first school type at the minimum learner count, so the dialog is fully
    readable before any JavaScript runs.
    """
    minimum = minimum_learners()
    types = school_types()
    default_type = types[0]['value'] if types else ''
    return {
        'pricing_school_types': types,
        'pricing_minimum_learners': minimum,
        'pricing_initial': quote(default_type, minimum),
        'pricing_rows': comparison_rows(minimum),
        'pricing_show_prepay': annual_prepay_months_billed() is not None,
        'pricing_show_funding_note': show_funding_explainer(),
        'pricing_mode': pricing_mode(),
        'pricing_quote_endpoint': '/subscription/enterprise-pricing',
        'pricing_redeem_url': '/subscription/redeem-package',
    }