r"""
Live check that the teacher side now shows the same three plan cards as the
parent side.

Signs in as both a parent and a teacher, then compares the plan-card markup and
confirms each role sees Individual, Family and Enterprise with the same prices.

    python verify_teacher_plans_live.py
"""

import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('VERIFY_BASE_URL', 'http://127.0.0.1:8000')
ACCOUNTS = {'parent': 'parent@sgila.test', 'teacher': 'teacher@sgila.test'}
PASSWORD = 'password123'

failures = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Session:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect()
        )

    def get(self, path):
        try:
            with self.opener.open(BASE + path) as response:
                return response.status, response.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode('utf-8', 'replace')

    def post(self, path, form, follow=False):
        """POSTs with the page's CSRF token, which the project requires."""
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', self.get(path)[1]
        )
        payload = dict(form)
        if token is not None:
            payload['csrfmiddlewaretoken'] = token.group(1)
        data = urllib.parse.urlencode(payload).encode()
        request = urllib.request.Request(BASE + path, data=data)
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        try:
            with self.opener.open(request) as response:
                return response.status, response.read().decode('utf-8', 'replace'), response.url
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode('utf-8', 'replace'), error.headers.get('Location', '')


def check(label, condition, detail=''):
    mark = 'PASS' if condition else 'FAIL'
    print(f'[{mark}] {label}' + (f' - {detail}' if detail else ''))
    if not condition:
        failures.append(label)


def sign_in(role, email):
    session = Session()
    _, page = session.get(f'/login?role={role}')
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page)
    if token is None:
        return None, ''
    session.post(
        f'/login?role={role}',
        {'csrfmiddlewaretoken': token.group(1), 'email': email,
         'password': PASSWORD, 'role': role},
    )
    return session, session.get('/subscription')


def cards_html(html):
    start = html.index('<div class="epic-cards">')
    end = html.index('</div>', html.index('Activate Enterprise Package')) + len('</div>')
    return re.sub(r'value="[^"]+"', 'value="CSRF"', html[start:end])


def main():
    print('=== Signing in as both roles ===')
    pages = {}
    for role, email in ACCOUNTS.items():
        session, page = sign_in(role, email)
        if session is None:
            check(f'{role} can sign in', False, 'no CSRF token on login page')
            continue
        status, html = page
        check(f'{role} can sign in and load /subscription', status == 200, f'status {status}')
        pages[role] = html

    if len(pages) != 2:
        print('\nCannot compare without both roles.')
        return 1

    print('\n--- Teacher sees the three plans ---')
    teacher = pages['teacher']
    for label in ('>Individual<', '>Family<', '>Enterprise<'):
        check(f'teacher sees {label.strip("<>")}', label in teacher)
    for fragment in (
        'R49<span>/month</span>',
        'R89<span>/month</span>',
        '/month per learner',
        'Minimum 100 learners',
        'Choose Individual Plan',
        'Choose Family Plan',
        'Activate Enterprise Package',
        'See full pricing details',
    ):
        check(f'teacher card has {fragment[:34]}', fragment in teacher)

    print('\n--- Cards are identical on both sides ---')
    parent_cards = cards_html(pages['parent'])
    teacher_cards = cards_html(teacher)
    check('plan card markup matches exactly', parent_cards == teacher_cards)
    if parent_cards != teacher_cards:
        print('  parent :', parent_cards[:160])
        print('  teacher:', teacher_cards[:160])

    print('\n--- Teacher gets the pricing dialog + school finder ---')
    check('dialog present', 'id="enterprise-pricing-dialog"' in teacher)
    check('province dropdown', 'data-sf-province' in teacher)
    check('school search box', 'data-sf-query' in teacher)
    check('finder script loaded', 'js/school_finder.js' in teacher)
    check('DBE footnote', 'National Master List of Schools' in teacher)
    check('comparison table', 'pricing-table' in teacher)
    check('close button', 'data-close-enterprise-pricing' in teacher)

    print('\n--- Old teacher tier cards removed ---')
    for gone in ('>Province / National<', '>District<', 'Enter package code'):
        check(f'{gone} is gone', gone not in teacher)

    print('\n--- Parent behaviour unchanged ---')
    parent = pages['parent']
    check('parent keeps the trial skip', 'continue with a free trial' in parent)
    check('parent keeps cancel link', '/subscription/cancel' in parent)
    check('teacher now gets the trial skip', 'continue with a free trial' in teacher)

    print('\n--- Teacher plan buttons reach the payment page ---')
    session, _ = sign_in('teacher', ACCOUNTS['teacher'])
    for plan in ('individual', 'family'):
        status, _, location = session.post('/subscription', {'plan': plan})
        check(
            f'teacher choosing {plan} lands on the payment page',
            status in (301, 302) and location.endswith('/subscription/payment'),
            f'status {status} -> {location}',
        )

        status, payment = session.get('/subscription/payment')
        check(f'teacher payment page loads for {plan}', status == 200, f'status {status}')
        check(
            f'teacher payment page names the {plan} plan price',
            'Add your payment details' in payment and '/month' in payment,
        )

    status, _, location = session.post('/subscription/payment', {
        'payment_method': 'card',
        'name_on_card': 'Live Teacher',
        'card_number': '4242424242424242',
        'expiry': '08/2028',
    })
    check(
        'teacher completing payment lands on the teacher dashboard',
        status in (301, 302) and location.endswith('/teacher/dashboard'),
        f'status {status} -> {location}',
    )

    print('\n--- Enterprise still activates with a package code ---')
    status, _, location = session.post('/subscription', {'plan': 'enterprise'})
    check(
        'teacher choosing enterprise lands on activation',
        status in (301, 302) and location.endswith('/subscription/redeem-package'),
        f'status {status} -> {location}',
    )

    status, redeem = session.get('/subscription/redeem-package')
    check('activation page loads for teacher', status == 200, f'status {status}')
    check('activation page has the school finder', 'data-sf-province' in redeem)

    print('\n--- Signed-out visitors can read every plan ---')
    guest = Session()
    status, guest_plans = guest.get('/subscription')
    check('plans page is public', status == 200, f'status {status}')
    for fragment in (
        '>Individual<', '>Family<', '>Enterprise<',
        'R49<span>/month</span>', 'R89<span>/month</span>',
        '/month per learner', 'Minimum 100 learners',
        '30-day free trial', 'href="/register"',
    ):
        check(f'public plans page has {fragment[:34]}', fragment in guest_plans)
    check('public plans page has no plan-choosing buttons', 'Choose Family Plan' not in guest_plans)
    check(
        'public plans page still has the full pricing dialog',
        'id="enterprise-pricing-dialog"' in guest_plans,
    )
    # A signed-out POST is rejected by CSRF before the view even sees it: the
    # read-only page carries no plan-choosing form, so there is no token to
    # post with. The view's own guard (redirect to /login) is covered by
    # PublicPlansPageTests.test_signed_out_visitors_cannot_submit_a_plan_choice.

    print('\n--- Teacher trial skip lands on their own dashboard ---')
    status, _, location = session.post('/subscription', {'skip': '1'})
    check(
        'teacher skipping the trial goes to the teacher dashboard',
        status in (301, 302) and location.endswith('/teacher/dashboard'),
        f'status {status} -> {location}',
    )

    print('\n--- Other plan routes still reachable ---')
    parent_session, _ = sign_in('parent', ACCOUNTS['parent'])
    status, _, location = parent_session.post('/subscription', {'skip': '1'})
    check(
        'parent skipping the trial goes to the parent dashboard',
        status in (301, 302) and location.endswith('/parent/dashboard'),
        f'status {status} -> {location}',
    )
    for path in ('/subscription/add-seat', '/subscription/cancel'):
        status, _ = parent_session.get(path)
        check(f'{path} reachable', status in (200, 302), f'status {status}')

    print('\n' + ('ALL LIVE CHECKS PASSED' if not failures else f'{len(failures)} FAILED: {failures}'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())