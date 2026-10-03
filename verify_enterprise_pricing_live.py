r"""
Live end-to-end check of the Enterprise pricing work against the dev server.

Logs in as a parent, reads /subscription, then exercises the calculator's quote
endpoint across school types, learner counts below the minimum and a large
number. Run with the dev server already listening on 127.0.0.1:8000:

    python verify_enterprise_pricing_live.py
"""

import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('VERIFY_BASE_URL', 'http://127.0.0.1:8000')
MODE = os.environ.get('VERIFY_PRICING_MODE', 'government_funded')
EMAIL = 'parent@sgila.test'
PASSWORD = 'password123'

LABELS = {
    'quintile_1': 'Quintile 1 (poorest)',
    'quintile_2': 'Quintile 2',
    'quintile_3': 'Quintile 3',
    'quintile_4': 'Quintile 4',
    'quintile_5': 'Quintile 5 (least poor)',
    'private': 'Private / independent school',
}

# What settings.PRICE_PER_LEARNER_MONTH says each mode should produce. Kept
# separate from the server so a mode switch that doesn't propagate to the page
# shows up as a failure rather than being silently accepted.
EXPECTED_BY_MODE = {
    'government_funded': {
        'start': 'R20',
        'funding_note': True,
        'prices': {
            'quintile_1': 'R40', 'quintile_2': 'R35', 'quintile_3': 'R30',
            'quintile_4': 'R25', 'quintile_5': 'R20', 'private': 'R20',
        },
    },
    'school_paid': {
        'start': 'R20',
        'funding_note': False,
        'prices': {
            'quintile_1': 'R20', 'quintile_2': 'R25', 'quintile_3': 'R30',
            'quintile_4': 'R35', 'quintile_5': 'R40', 'private': 'R40',
        },
    },
}
EXPECTED = EXPECTED_BY_MODE[MODE]

failures = []


class Session:
    """Minimal cookie-keeping HTTP client so no third-party dependency is needed."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            NoRedirect(),
        )

    def request(self, path, params=None, form=None, follow=False):
        url = BASE + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(url, data=data)
        if data:
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        last = None
        for _ in range(6 if follow else 1):
            try:
                with self.opener.open(req) as response:
                    return response.status, response.read().decode('utf-8', 'replace')
            except urllib.error.HTTPError as error:
                last = (error.code, error.read().decode('utf-8', 'replace'))
                if follow and error.code in (301, 302, 303, 307, 308):
                    location = error.headers.get('Location', '')
                    req = urllib.request.Request(BASE + location, data=None)
                    if location.startswith(BASE):
                        req = urllib.request.Request(location, data=None)
                    continue
                return last
        return last

    def get(self, path, params=None, follow=False):
        return self.request(path, params=params, follow=follow)

    def post(self, path, form=None, follow=False):
        return self.request(path, form=form or {}, follow=follow)

    def get_json(self, path, params=None):
        status, body = self.get(path, params=params)
        return status, json.loads(body)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check(label, condition, detail=''):
    mark = 'PASS' if condition else 'FAIL'
    print(f'[{mark}] {label}' + (f' - {detail}' if detail else ''))
    if not condition:
        failures.append(label)


def card_price(html):
    match = re.search(r'<p class="epic-price"><span>From</span>\s*([^<]+)<span>', html)
    return match.group(1).strip() if match else None


def main():
    session = Session()

    # The login form is CSRF-protected, so pick the token up from the page first.
    _, login_page = session.get('/login?role=parent')
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page)
    check('login page exposes a CSRF token', token is not None)
    if token is None:
        return 1

    login_status, _ = session.post('/login?role=parent', form={
        'csrfmiddlewaretoken': token.group(1),
        'email': EMAIL,
        'password': PASSWORD,
        'role': 'parent',
    })
    check('parent can log in', login_status in (302, 200), f'status {login_status}')

    page_status, html = session.get('/subscription')
    check('/subscription returns 200', page_status == 200, f'status {page_status}')

    print('\n--- Enterprise card ---')
    price = card_price(html)
    print(f'     card price: {price!r}')
    check('card shows a per-learner monthly price', price is not None and price.startswith('R'))
    check('card advertises the lowest price in the active table', price == EXPECTED['start'])
    check('card no longer shows the old yearly figure', 'R8,400' not in html)
    check('card says "/month per learner"', '/month per learner' in html)
    check('card shows the 100-learner minimum', 'Minimum 100 learners' in html)
    check('card subtitle kept', 'For schools &amp; shared accounts' in html)
    check('card keeps the details link', 'See full pricing details' in html)
    check('card keeps the activate button', 'Activate Enterprise Package' in html)
    check('card heading class kept (teal)', 'epic-card-enterprise' in html)

    print('\n--- Individual / Family untouched ---')
    check('Individual still R49/month', 'R49<span>/month</span>' in html)
    check('Family still R89/month', 'R89<span>/month</span>' in html)
    check('trial skip link intact', 'free trial' in html)
    check('add-seat link intact', '/subscription/add-seat' in html)
    check('cancel link intact', '/subscription/cancel' in html)

    print('\n--- Modal markup ---')
    check('modal present', 'id="enterprise-pricing-dialog"' in html)
    check('old "How school pricing works" title gone', 'How school pricing works' not in html)
    check('school type dropdown present (manual fallback)', 'data-sf-manual-type' in html)
    check('learner number input present', 'type="number"' in html)
    check('learner input min is the minimum', re.search(r'data-sf-learners[^>]*min="100"', html) is not None)
    check('quintile note present', "Department of Basic Education's school poverty" in html)
    check('close button present', 'data-close-enterprise-pricing' in html)
    check('comparison table present', 'pricing-table' in html)
    check('billed-to-school copy present', 'billed to the school' in html)
    check(
        f'funding-explainer line {"shown" if EXPECTED["funding_note"] else "hidden"} in {MODE}',
        ('receive more state funding' in html) == EXPECTED['funding_note'],
    )
    check('annual prepay hidden by default', 'pricing-result-row-prepay' not in html)
    for label in ('Quintile 1', 'Quintile 5', 'Private / independent school'):
        check(f'table lists {label}', label in html)

    print('\n--- School finder in the modal ---')
    check('province dropdown present', 'data-sf-province' in html)
    for province in ('Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal',
                     'Limpopo', 'Mpumalanga', 'Northern Cape', 'North West',
                     'Western Cape'):
        check(f'province option {province}', f'>{province}</option>' in html)
    check('school name search box present', 'data-sf-query' in html)
    check('search box is a combobox', 'role="combobox"' in html)
    check('suggestions listbox present', 'role="listbox"' in html)
    check(
        'manual fallback prompt present',
        # Django escapes the apostrophe, so compare on the part that survives.
        'Select your school type manually' in html,
    )
    check('"Not sure" option present', 'data-sf-not-sure' in html)
    check('DBE footnote present', 'National Master List of Schools' in html)
    check('search endpoint wired', 'data-sf-search="/api/schools/search/"' in html)
    check('quote endpoint wired', 'data-sf-quote="/subscription/enterprise-pricing"' in html)
    check('finder script loaded', 'js/school_finder.js' in html)

    print('\n--- Comparison table figures match the active mode ---')
    for school_type, per in EXPECTED['prices'].items():
        label = LABELS[school_type]
        check(f'table shows {label} at {per}', f'<th scope="row">{label}</th>' in html
              and re.search(
                  re.escape(label) + r'</th>\s*<td>' + re.escape(per) + r'</td>',
                  html) is not None)

    print('\n--- Quote endpoint ---')
    cases = [
        ('quintile_1', 100),
        ('quintile_2', 250),
        ('quintile_3', 1000),
        ('quintile_4', 137),
        ('quintile_5', 1000),
        ('private', 100),
    ]
    for school_type, learners in cases:
        per = EXPECTED['prices'][school_type]
        per_value = int(per.lstrip('R'))
        month = f'R{per_value * learners:,}'
        year = f'R{per_value * learners * 12:,}'
        expected_breakdown = f'{learners:,} learners x {per} = {month}/month'
        status, data = session.get_json(
            '/subscription/enterprise-pricing',
            {'school_type': school_type, 'learners': learners},
        )
        ok = (
            status == 200
            and data['valid'] is True
            and data['per_learner_month'] == per
            and data['total_month'] == month
            and data['total_year'] == year
            and data['breakdown'] == expected_breakdown
            and data['pricing_mode'] == MODE
        )
        check(
            f'{school_type} x {learners}',
            ok,
            f"{data.get('per_learner_month')} / {data.get('total_month')} / {data.get('total_year')}",
        )

    print('\n--- Validation ---')
    _, low = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_2', 'learners': 99},
    )
    check('learners below 100 is invalid', low['valid'] is False)
    check('below-minimum message is friendly', '100 learners' in low['error'], low['error'])
    check('below-minimum returns no figures', low['total_month'] is None)

    _, blank = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_2', 'learners': ''},
    )
    check('blank learners is invalid', blank['valid'] is False)
    check('blank learners asks for a number', 'how many learners' in blank['error'], blank['error'])

    _, junk = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_2', 'learners': 'many'},
    )
    check('junk learners is invalid', junk['valid'] is False)

    _, exact = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_2', 'learners': 100},
    )
    check('exactly 100 learners is valid', exact['valid'] is True)

    bad_status, _ = session.get(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_9', 'learners': 250},
    )
    check('unknown school type is rejected with 400', bad_status == 400, f'status {bad_status}')

    _, thousands = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'private', 'learners': '1,000'},
    )
    private_thousand = f"R{int(EXPECTED['prices']['private'].lstrip('R')) * 1000:,}"
    check(
        'comma-separated 1,000 works',
        thousands['total_month'] == private_thousand,
        thousands.get('total_month'),
    )

    _, prepay_off = session.get_json(
        '/subscription/enterprise-pricing',
        {'school_type': 'quintile_2', 'learners': 250},
    )
    check('annual prepay hidden by default', prepay_off.get('annual_prepay') is None)

    carried_total = f"R{int(EXPECTED['prices']['quintile_2'].lstrip('R')) * 250:,} per month"
    print('\n--- Handover to activation ---')
    redeem_status, redeem_html = session.get(
        '/subscription/redeem-package',
        {'school_type': 'quintile_2', 'learners': 250},
    )
    check('redeem page returns 200', redeem_status == 200)
    check('redeem page echoes the school type', 'Quintile 2' in redeem_html)
    check('redeem page echoes the learner count', '250 learners' in redeem_html)
    check('redeem page shows the carried total', carried_total in redeem_html, carried_total)
    check('redeem page still asks for a package code', 'name="package_code"' in redeem_html)
    check('redeem page no longer hard-codes R7', 'R7 per learner' not in redeem_html)

    plain_status, plain_html = session.get('/subscription/redeem-package')
    check('redeem page works with no hand-off', plain_status == 200)
    check('no fabricated estimate without a hand-off', 'Your estimate' not in plain_html)

    print('\n--- Individual / Family flows still work ---')
    seat_status, _ = session.get('/subscription/add-seat')
    check('add-seat route reachable', seat_status in (200, 302), f'status {seat_status}')
    cancel_status, _ = session.get('/subscription/cancel')
    check('cancel route reachable', cancel_status in (200, 302), f'status {cancel_status}')

    live_school_checks(session)

    print('\n' + ('ALL LIVE CHECKS PASSED' if not failures else f'{len(failures)} FAILED: {failures}'))
    return 1 if failures else 0


def live_school_checks(session):
    """Exercises the real school search against whatever is in the local database."""
    print('\n--- School search API ---')

    status, payload = session.get_json('/api/schools/search/', {'province': 'Eastern Cape', 'q': 'baleni'})
    check('search returns 200', status == 200, f'status {status}')
    if status != 200:
        return
    results = payload.get('results', [])
    check('search finds schools', len(results) > 0, f'{len(results)} results')
    if results:
        first = results[0]
        for field in ('id', 'name', 'province', 'quintile', 'sector',
                      'learners_2025', 'price_per_learner_month',
                      'prefilled_learners', 'display_label'):
            check(f'result carries {field}', field in first)
        check(
            'display label includes the name',
            first['name'] in first['display_label'],
            first['display_label'],
        )
        check('at most 10 results', len(results) <= 10, f'{len(results)}')

    status, payload = session.get_json('/api/schools/search/', {'q': 'baleni'})
    check('province is required', status == 400, f'status {status}')
    check('province_required code', payload.get('code') == 'province_required')
    check('nine provinces offered', len(payload.get('provinces', [])) == 9)

    status, payload = session.get_json('/api/schools/search/', {'province': 'Eastern Cape', 'q': 'ba'})
    check('short query rejected', status == 400, f'status {status}')
    check('query_too_short code', payload.get('code') == 'query_too_short')

    _, payload = session.get_json(
        '/api/schools/search/', {'province': 'Eastern Cape', 'q': 'zzzznotaschool'}
    )
    check('no results returns an empty list', payload.get('count') == 0)

    # Same name in one province must be disambiguated by town/district.
    _, payload = session.get_json(
        '/api/schools/search/', {'province': 'Eastern Cape', 'q': 'zamokuhle junior'}
    )
    results = payload.get('results', [])
    if len(results) > 1:
        labels = {r['display_label'] for r in results}
        check(
            'duplicate names are told apart by town/district',
            len(labels) == len(results),
            f'{len(results)} results, {len(labels)} distinct labels',
        )
    else:
        check('duplicate-name search found the repeat', False, f'{len(results)} results')

    print('\n--- Redeem page school finder ---')
    redeem_status, redeem_html = session.get('/subscription/redeem-package')
    check('redeem page returns 200', redeem_status == 200)
    check('redeem page has the province dropdown', 'data-sf-province' in redeem_html)
    check('redeem page has the school search box', 'data-sf-query' in redeem_html)
    check('redeem page keeps the School name field', 'name="school_name"' in redeem_html)
    check('redeem page keeps the Package code field', 'name="package_code"' in redeem_html)
    check('redeem page loads the finder script', 'js/school_finder.js' in redeem_html)
    check('redeem page carries the DBE footnote', 'National Master List of Schools' in redeem_html)
    check('redeem page auto-fills the school name field', 'data-sf-autofill-name="redeem"' in redeem_html)

    print('\n--- Preselection by school id ---')
    _, payload = session.get_json(
        '/api/schools/search/', {'province': 'Eastern Cape', 'q': 'baleni secondary'}
    )
    results = payload.get('results', [])
    if results:
        target = results[0]
        status, html = session.get('/subscription/redeem-package', {
            'school_id': target['id'],
            'school_type': target['price_school_type'] or '',
            'learners': target['prefilled_learners'],
        })
        check('redeem page accepts a school_id', status == 200, f'status {status}')
        check('school name auto-filled from the id', f'value="{target["name"]}"' in html)
        check('province preselected', 'data-sf-preselect-json' in html)

    status, _ = session.get('/subscription/redeem-package', {'school_id': '99999999'})
    check('unknown school_id degrades gracefully', status == 200, f'status {status}')
    status, _ = session.get('/subscription/redeem-package', {'school_id': 'not-a-number'})
    check('bogus school_id degrades gracefully', status == 200, f'status {status}')


if __name__ == '__main__':
    sys.exit(main())