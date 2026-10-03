import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase, override_settings

from api.models import Parent, Subscription, Teacher
from lessons import pricing
from sgila_project import settings as project_settings


class FormatRandTests(TestCase):
	def test_whole_rands_have_no_decimals(self):
		self.assertEqual(pricing.format_rand(20), 'R20')
		self.assertEqual(pricing.format_rand(1234), 'R1,234')
		self.assertEqual(pricing.format_rand(40000), 'R40,000')

	def test_cents_are_kept_to_two_places(self):
		self.assertEqual(pricing.format_rand(Decimal('1234.5')), 'R1,234.50')
		self.assertEqual(pricing.format_rand(Decimal('8.75')), 'R8.75')

	def test_rounds_half_up_to_two_decimals(self):
		self.assertEqual(pricing.format_rand(Decimal('8.005')), 'R8.01')
		self.assertEqual(pricing.format_rand(Decimal('250.567')), 'R250.57')

	def test_zero_renders_as_r0(self):
		self.assertEqual(pricing.format_rand(0), 'R0')


@override_settings(
	PRICING_MODE='government_funded',
	PRICE_PER_LEARNER_MONTH={
		'government_funded': {
			'quintile_1': 40, 'quintile_2': 35, 'quintile_3': 30,
			'quintile_4': 25, 'quintile_5': 20, 'private': 20,
		},
		'school_paid': {
			'quintile_1': 20, 'quintile_2': 25, 'quintile_3': 30,
			'quintile_4': 35, 'quintile_5': 40, 'private': 40,
		},
	},
	ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=20,
	ANNUAL_PREPAY_MONTHS_BILLED=None,
)
class GovernmentFundedQuoteTests(TestCase):
	def test_start_price_is_the_lowest_active_price(self):
		self.assertEqual(pricing.format_rand(pricing.start_price_per_learner_month()), 'R20')

	def test_poorest_schools_pay_the_most(self):
		self.assertEqual(pricing.format_rand(pricing.price_per_learner_month('quintile_1')), 'R40')
		self.assertEqual(pricing.format_rand(pricing.price_per_learner_month('quintile_5')), 'R20')

	def test_quote_multiplies_out_to_month_and_year(self):
		quote = pricing.quote('quintile_2', 250)

		self.assertTrue(quote['valid'])
		self.assertEqual(quote['per_learner_month'], 'R35')
		self.assertEqual(quote['total_month'], 'R8,750')
		self.assertEqual(quote['total_year'], 'R105,000')
		self.assertEqual(quote['breakdown'], '250 learners x R35 = R8,750/month')

	def test_quote_for_a_thousand_learners(self):
		quote = pricing.quote('private', 1000)

		self.assertEqual(quote['per_learner_month'], 'R20')
		self.assertEqual(quote['total_month'], 'R20,000')
		self.assertEqual(quote['total_year'], 'R240,000')

	def test_funding_explainer_is_shown_in_this_mode(self):
		self.assertTrue(pricing.show_funding_explainer())

	def test_no_prepay_line_when_the_discount_is_off(self):
		self.assertIsNone(pricing.annual_prepay_months_billed())
		self.assertIsNone(pricing.quote('quintile_3', 120)['annual_prepay'])


@override_settings(
	PRICING_MODE='school_paid',
	PRICE_PER_LEARNER_MONTH={
		'government_funded': {
			'quintile_1': 40, 'quintile_2': 35, 'quintile_3': 30,
			'quintile_4': 25, 'quintile_5': 20, 'private': 20,
		},
		'school_paid': {
			'quintile_1': 20, 'quintile_2': 25, 'quintile_3': 30,
			'quintile_4': 35, 'quintile_5': 40, 'private': 40,
		},
	},
	ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=20,
	ANNUAL_PREPAY_MONTHS_BILLED=None,
)
class SchoolPaidQuoteTests(TestCase):
	def test_prices_rise_with_the_schools_ability_to_pay(self):
		self.assertEqual(pricing.format_rand(pricing.price_per_learner_month('quintile_1')), 'R20')
		self.assertEqual(pricing.format_rand(pricing.price_per_learner_month('quintile_5')), 'R40')
		self.assertEqual(pricing.format_rand(pricing.price_per_learner_month('private')), 'R40')

	def test_funding_explainer_is_hidden_in_this_mode(self):
		self.assertFalse(pricing.show_funding_explainer())


class LearnerValidationTests(TestCase):
	def test_learners_below_the_minimum_are_rejected_with_a_friendly_message(self):
		quote = pricing.quote('quintile_2', 99)

		self.assertFalse(quote['valid'])
		self.assertIn('100 learners', quote['error'])
		self.assertIsNone(quote['total_month'])

	def test_exactly_the_minimum_is_allowed(self):
		self.assertTrue(pricing.quote('quintile_2', 100)['valid'])

	def test_blank_learners_asks_for_a_number(self):
		quote = pricing.quote('quintile_2', None)

		self.assertFalse(quote['valid'])
		self.assertIn('how many learners', quote['error'])

	def test_non_numeric_learners_are_treated_as_blank(self):
		self.assertIsNone(pricing.parse_learners('many'))
		self.assertIsNone(pricing.parse_learners(''))
		self.assertIsNone(pricing.parse_learners(None))

	def test_thousands_separators_are_tolerated(self):
		self.assertEqual(pricing.parse_learners('1,000'), 1000)
		self.assertEqual(pricing.parse_learners(' 250 '), 250)

	def test_unknown_school_type_is_rejected(self):
		quote = pricing.quote('quintile_99', 250)

		self.assertFalse(quote['valid'])
		self.assertEqual(quote['error'], 'Please choose your school type.')


@override_settings(
	PRICING_MODE='government_funded',
	PRICE_PER_LEARNER_MONTH={
		'government_funded': {
			'quintile_1': 40, 'quintile_2': 35, 'quintile_3': 30,
			'quintile_4': 25, 'quintile_5': 20, 'private': 20,
		},
	},
	ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=20,
	ANNUAL_PREPAY_MONTHS_BILLED=10,
)
class AnnualPrepayTests(TestCase):
	def test_pay_ten_months_get_twelve(self):
		self.assertEqual(pricing.annual_prepay_months_billed(), 10)

		prepay = pricing.quote('quintile_2', 250)['annual_prepay']

		self.assertEqual(prepay['months_billed'], 10)
		self.assertEqual(prepay['months_free'], 2)
		self.assertEqual(prepay['total'], 'R87,500')
		self.assertIn('12 months', prepay['note'])

	def test_monthly_and_yearly_totals_are_still_shown_alongside_it(self):
		quote = pricing.quote('quintile_2', 250)

		self.assertEqual(quote['total_month'], 'R8,750')
		self.assertEqual(quote['total_year'], 'R105,000')


class ComparisonRowTests(TestCase):
	def test_every_school_type_has_a_row_at_the_minimum(self):
		rows = pricing.comparison_rows()

		self.assertEqual(len(rows), len(pricing.school_types()))
		self.assertEqual(rows[0]['per_learner_month'], 'R40')
		self.assertEqual(rows[0]['minimum_total_month'], 'R4,000')

	def test_rows_never_below_the_minimum_learner_count(self):
		rows = pricing.comparison_rows(learners=10)

		self.assertEqual(rows[0]['minimum_total_month'], 'R4,000')


class EnterpriseQuoteEndpointTests(TestCase):
	def setUp(self):
		self.client = Client()
		parent = Parent.objects.create(
			full_name='Pricing Parent',
			email='pricing-parent@example.com',
			password='not-a-real-password',
		)
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = parent.id
		session.save()

	def test_endpoint_returns_a_formatted_quote(self):
		response = self.client.get(
			'/subscription/enterprise-pricing',
			{'school_type': 'quintile_2', 'learners': '250'},
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload['valid'])
		self.assertEqual(payload['per_learner_month'], 'R35')
		self.assertEqual(payload['total_month'], 'R8,750')
		self.assertEqual(payload['total_year'], 'R105,000')
		self.assertEqual(payload['breakdown'], '250 learners x R35 = R8,750/month')

	def test_endpoint_reports_the_minimum_learner_error(self):
		response = self.client.get(
			'/subscription/enterprise-pricing',
			{'school_type': 'quintile_1', 'learners': '40'},
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertFalse(payload['valid'])
		self.assertIn('100 learners', payload['error'])

	def test_endpoint_rejects_an_unknown_school_type(self):
		response = self.client.get(
			'/subscription/enterprise-pricing',
			{'school_type': 'nope', 'learners': '250'},
		)

		self.assertEqual(response.status_code, 400)

	def test_endpoint_handles_a_thousand_learners(self):
		response = self.client.get(
			'/subscription/enterprise-pricing',
			{'school_type': 'private', 'learners': '1,000'},
		)

		payload = response.json()
		self.assertEqual(payload['total_month'], 'R20,000')
		self.assertEqual(payload['total_year'], 'R240,000')


class SubscriptionPagePricingTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.parent = Parent.objects.create(
			full_name='Card Parent',
			email='card-parent@example.com',
			password='not-a-real-password',
		)
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = self.parent.id
		session.save()

	def test_card_shows_the_per_learner_month_price_not_the_old_yearly_figure(self):
		response = self.client.get('/subscription')

		self.assertNotContains(response, 'R8,400')
		self.assertNotContains(response, '/year')
		self.assertContains(response, 'From</span> R20<span>/month per learner</span>')
		self.assertContains(response, 'Minimum 100 learners')
		self.assertContains(response, 'See full pricing details')
		self.assertContains(response, 'Activate Enterprise Package')

	def test_card_price_comes_from_config(self):
		with self.settings(ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=33.5):
			response = self.client.get('/subscription')

		self.assertContains(response, 'From</span> R33.50<span>/month per learner</span>')

	def test_modal_lists_every_school_type(self):
		response = self.client.get('/subscription')

		for label, _ in project_settings.SCHOOL_TYPES:
			self.assertContains(response, label)

	def test_funding_note_appears_in_government_funded_mode(self):
		response = self.client.get('/subscription')

		self.assertContains(response, 'receive more state funding')

	def test_funding_note_is_absent_in_school_paid_mode(self):
		with self.settings(PRICING_MODE='school_paid'):
			response = self.client.get('/subscription')

		self.assertNotContains(response, 'receive more state funding')

	def test_individual_and_family_prices_are_untouched(self):
		response = self.client.get('/subscription')

		self.assertContains(response, 'R49<span>/month</span>')
		self.assertContains(response, 'R89<span>/month</span>')
		self.assertContains(response, '/subscription/add-seat')
		self.assertContains(response, '/subscription/cancel')


class PlanPriceConfigTests(TestCase):
	"""
	The flat monthly prices live in settings and are rendered by
	``lessons.pricing``, so no template can quote a stale figure.
	"""

	def test_prices_are_read_from_settings(self):
		with self.settings(SUBSCRIPTION_PRICES={'individual': 55, 'family': 95}):
			prices = pricing.plan_prices()

		self.assertEqual(prices, {'individual': 'R55', 'family': 'R95'})

	def test_plan_price_rounds_like_every_other_price(self):
		with self.settings(SUBSCRIPTION_PRICES={'individual': 49.005, 'family': 89}):
			self.assertEqual(pricing.format_rand(pricing.plan_price('individual')), 'R49.01')

	def test_cards_follow_a_configured_price_change(self):
		parent = Parent.objects.create(
			full_name='Config Parent',
			email='config-parent@example.com',
			password='not-a-real-password',
		)
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = parent.id
		session.save()

		with self.settings(SUBSCRIPTION_PRICES={'individual': 60, 'family': 100}):
			response = self.client.get('/subscription')

		self.assertContains(response, 'R60<span>/month</span>')
		self.assertContains(response, 'R100<span>/month</span>')

	def test_enterprise_is_not_part_of_the_flat_price_table(self):
		self.assertNotIn('enterprise', project_settings.SUBSCRIPTION_PRICES)


class PlanCardSizingTests(TestCase):
	"""
	The three plan cards must render at one identical height. Each card's CTA is
	pinned to the bottom with `margin-top: auto`, so if the Enterprise price line
	wraps onto a second row that card grows and the extra height surfaces as dead
	space above the Individual and Family buttons. These guard the two rules that
	prevent that.
	"""

	def setUp(self):
		self.stylesheet = (
			Path(settings.BASE_DIR) / 'static' / 'css' / 'sgila_app.css'
		).read_text(encoding='utf-8')

	def test_card_container_stretches_children_to_one_height(self):
		self.assertRegex(
			self.stylesheet,
            r'\.epic-cards\s*\{[^}]*align-items:\s*stretch',
		)

	def test_enterprise_price_qualifiers_are_sized_to_fit_one_line(self):
		self.assertIn('.epic-card-enterprise .epic-price span', self.stylesheet)
		self.assertRegex(
			self.stylesheet,
            r'\.epic-card-enterprise \.epic-price\s*\{\s*white-space:\s*nowrap',
		)

	def test_all_three_cards_share_the_same_base_class(self):
		parent = Parent.objects.create(
			full_name='Sizing Parent',
			email='sizing-parent@example.com',
			password='not-a-real-password',
		)
		client = Client()
		session = client.session
		session['account_role'] = 'parent'
		session['account_id'] = parent.id
		session.save()

		body = client.get('/subscription').content.decode()

		self.assertEqual(body.count('epic-card '), 3)
		self.assertIn('epic-card-individual', body)
		self.assertIn('epic-card-family', body)
		self.assertIn('epic-card-enterprise', body)

	def test_no_card_content_was_dropped(self):
		parent = Parent.objects.create(
			full_name='Content Parent',
			email='content-parent@example.com',
			password='not-a-real-password',
		)
		client = Client()
		session = client.session
		session['account_role'] = 'parent'
		session['account_id'] = parent.id
		session.save()

		body = client.get('/subscription').content.decode()

		for expected in (
			'For 1 child',
			'Choose Individual Plan',
			'For up to 4 children',
			'Choose Family Plan',
			'For schools &amp; shared accounts',
			'Minimum 100 learners',
			'See full pricing details',
			'Activate Enterprise Package',
		):
			self.assertIn(expected, body)


class TeacherPlanCardsTests(TestCase):
	"""
	The teacher view shows the same three plans as the parent view — Individual,
	Family and Enterprise — rendered from the same partial, so the two cannot
	drift apart.
	"""

	def setUp(self):
		self.client = Client()
		self.parent = Parent.objects.create(
			full_name='Plan Parent',
			email='plan-parent@example.com',
			password='not-a-real-password',
		)
		self.teacher = Teacher.objects.create(
			full_name='Plan Teacher',
			email='plan-teacher@example.com',
			password='not-a-real-password',
		)

	def sign_in(self, role, account):
		session = self.client.session
		session['account_role'] = role
		session['account_id'] = account.id
		session.save()

	def cards_html(self):
		"""
		Just the three plan cards, for comparing across roles.

		The CSRF token is a fresh random value on every request, so it is
		normalised away; everything else must match exactly.
		"""
		html = self.client.get('/subscription').content.decode()
		start = html.index('<div class="epic-cards">')
		end = html.index('</div>', html.index('Activate Enterprise Package')) + len('</div>')
		cards = html[start:end]
		return re.sub(r'value="[^"]+"', 'value="CSRF"', cards)

	def test_teacher_sees_the_same_three_plans(self):
		self.sign_in('teacher', self.teacher)
		response = self.client.get('/subscription')
		body = response.content.decode()

		self.assertContains(response, '>Individual<')
		self.assertContains(response, '>Family<')
		self.assertContains(response, '>Enterprise<')
		self.assertContains(response, 'R49<span>/month</span>')
		self.assertContains(response, 'R89<span>/month</span>')
		self.assertContains(response, '/month per learner')
		self.assertContains(response, 'Choose Individual Plan')
		self.assertContains(response, 'Choose Family Plan')
		self.assertContains(response, 'Activate Enterprise Package')
		self.assertContains(response, 'See full pricing details')

	def test_teacher_cards_are_identical_to_parent_cards(self):
		self.sign_in('parent', self.parent)
		parent_cards = self.cards_html()
		self.client = Client()
		self.sign_in('teacher', self.teacher)
		teacher_cards = self.cards_html()

		self.assertEqual(parent_cards, teacher_cards)

	def test_teacher_gets_the_same_pricing_dialog_with_the_school_finder(self):
		self.sign_in('teacher', self.teacher)
		body = self.client.get('/subscription').content.decode()

		self.assertIn('id="enterprise-pricing-dialog"', body)
		self.assertIn('data-sf-province', body)
		self.assertIn('data-sf-query', body)
		self.assertIn('js/school_finder.js', body)
		self.assertIn('National Master List of Schools', body)

	def test_teacher_enterprise_card_prices_from_config(self):
		with self.settings(ENTERPRISE_START_PRICE_PER_LEARNER_MONTH=29):
			self.sign_in('teacher', self.teacher)
			response = self.client.get('/subscription')
		self.assertContains(response, 'From</span> R29<span>/month per learner</span>')

	def test_teacher_gets_the_same_free_trial_treatment(self):
		# A teacher's Subscription is created in 'trial' status and their dashboard
		# is gated on that trial lapsing, so the trial offer is honest for them too.
		self.sign_in('teacher', self.teacher)
		body = self.client.get('/subscription').content.decode()

		self.assertIn('All teacher plans include a', body)
		self.assertIn('30-day trial', body)
		self.assertIn('Not right now — continue with a free trial', body)
		self.assertIn('name="skip" value="1"', body)
		self.assertIn('class="epic-skip"', body)

	def test_teacher_trial_skip_goes_to_their_dashboard(self):
		self.sign_in('teacher', self.teacher)
		response = self.client.post('/subscription', {'skip': '1'})

		self.assertRedirects(
			response, '/teacher/dashboard', fetch_redirect_response=False
		)
		subscription = self.teacher.subscription
		self.assertEqual(subscription.status, 'trial')
		self.assertFalse(subscription.is_trial_expired)

	def test_parent_trial_skip_still_goes_to_the_parent_dashboard(self):
		self.sign_in('parent', self.parent)
		response = self.client.post('/subscription', {'skip': '1'})
		self.assertRedirects(response, '/parent/dashboard', fetch_redirect_response=False)

	def test_teacher_choosing_a_card_plan_goes_to_the_same_payment_page(self):
		# Individual and Family are card-paid for teachers exactly as they are
		# for parents: the choice is parked as 'pending' and the payment screen
		# collects the details. Enterprise stays on the package-code screen.
		self.sign_in('teacher', self.teacher)
		for plan in ('individual', 'family'):
			self.client = Client()
			self.sign_in('teacher', self.teacher)
			response = self.client.post('/subscription', {'plan': plan})
			self.assertRedirects(
				response, '/subscription/payment', fetch_redirect_response=False
			)

			subscription = Subscription.objects.get(teacher=self.teacher)
			self.assertEqual(subscription.plan_type, plan)
			self.assertEqual(subscription.billing_cycle, 'monthly')
			self.assertEqual(subscription.status, 'pending')

	def test_teacher_choosing_enterprise_still_goes_to_package_activation(self):
		self.sign_in('teacher', self.teacher)
		response = self.client.post('/subscription', {'plan': 'enterprise'})
		self.assertRedirects(
			response, '/subscription/redeem-package', fetch_redirect_response=False
		)
		# Enterprise is not a card plan, so the choice must not be parked.
		self.assertEqual(self.teacher.subscription.status, 'trial')

	def test_teacher_payment_page_completes_back_to_the_teacher_dashboard(self):
		self.sign_in('teacher', self.teacher)
		self.client.post('/subscription', {'plan': 'family'})

		page = self.client.get('/subscription/payment')
		self.assertEqual(page.status_code, 200)
		self.assertContains(page, 'Family')
		self.assertContains(page, 'R89/month')
		self.assertContains(page, 'your teacher dashboard')

		response = self.client.post('/subscription/payment', {
			'payment_method': 'card',
			'name_on_card': 'Plan Teacher',
			'card_number': '4242424242424242',
			'expiry': '08/2028',
		})
		self.assertRedirects(response, '/teacher/dashboard')

		subscription = self.teacher.subscription
		self.assertEqual(subscription.status, 'active')
		self.assertEqual(subscription.plan_type, 'family')
		self.assertEqual(subscription.card_last4, '4242')

	def test_teacher_payment_page_is_also_reachable_with_bank_details(self):
		self.sign_in('teacher', self.teacher)
		self.client.post('/subscription', {'plan': 'individual'})

		response = self.client.post('/subscription/payment', {
			'payment_method': 'debit_order',
			'account_holder': 'Plan Teacher',
			'bank_name': 'Standard Bank',
			'account_number': '123456789',
			'branch_code': '051001',
		})

		self.assertRedirects(response, '/teacher/dashboard')
		subscription = self.teacher.subscription
		self.assertEqual(subscription.payment_method, 'debit_order')
		self.assertEqual(subscription.account_last4, '6789')

	def test_teacher_payment_page_keeps_the_form_when_card_details_are_bad(self):
		self.sign_in('teacher', self.teacher)
		self.client.post('/subscription', {'plan': 'individual'})

		response = self.client.post('/subscription/payment', {
			'payment_method': 'card',
			'name_on_card': '',
			'card_number': '4242',
			'expiry': '',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Please fill in all card details correctly.')
		self.assertEqual(self.teacher.subscription.status, 'pending')

	def test_payment_page_without_a_chosen_plan_goes_back_to_plans(self):
		# A teacher signing in fresh has no plan picked yet, so there is nothing
		# to pay for — send them back to the plan list rather than a dead form.
		self.sign_in('teacher', self.teacher)
		response = self.client.get('/subscription/payment')
		self.assertRedirects(response, '/subscription', fetch_redirect_response=False)

	def test_anonymous_visitor_is_sent_to_sign_in_from_the_payment_page(self):
		response = self.client.get('/subscription/payment')
		self.assertRedirects(response, '/login', fetch_redirect_response=False)

	def test_replaced_teacher_tier_cards_are_gone(self):
		self.sign_in('teacher', self.teacher)
		body = self.client.get('/subscription').content.decode()

		self.assertNotIn('>Province / National<', body)
		self.assertNotIn('>District<', body)
		self.assertNotIn('Enter package code', body)


class WelcomePagePlansLinkTests(TestCase):
	"""
	The signed-out homepage nav links to Plans, sitting next to "For schools".
	Signed-in visitors already get a "Plan" link in the main nav, so the homepage
	nav is intentionally limited to logged-out visitors.
	"""

	def test_homepage_nav_has_a_plans_link_next_to_for_schools(self):
		body = self.client.get('/').content.decode()

		self.assertIn('<div class="home-nav-links"', body)
		nav = body[body.index('<div class="home-nav-links"'):]
		nav = nav[:nav.index('</div>')]

		self.assertIn('>For schools<', nav)
		self.assertIn('>Plans<', nav)
		self.assertIn('href="/subscription"', nav)
		self.assertLess(
			nav.index('>For schools<'),
			nav.index('>Plans<'),
			'Plans should follow "For schools"',
		)

	def test_homepage_nav_keeps_the_other_section_links(self):
		body = self.client.get('/').content.decode()
		for link in ('>Stories<', '>For families<', '>For schools<'):
			self.assertIn(link, body)

	def test_signed_in_visitors_do_not_see_the_homepage_nav(self):
		parent = Parent.objects.create(
			full_name='Nav Parent', email='nav-parent@example.com',
			password='not-a-real-password',
		)
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = parent.id
		session.save()

		body = self.client.get('/').content.decode()
		self.assertNotIn('home-nav-links', body)

	def test_plans_link_is_hidden_on_other_pages(self):
		body = self.client.get('/login').content.decode()
		self.assertNotIn('home-nav-links', body)


class PublicPlansPageTests(TestCase):
	"""
	The "Plans" link on the signed-out homepage nav has to land somewhere
	useful, so /subscription is readable without an account: every plan, every
	price, no plan-choosing buttons. Choosing a plan still needs a sign-in.
	"""

	def setUp(self):
		self.client = Client()
		self.parent = Parent.objects.create(
			full_name='Public Parent',
			email='public-parent@example.com',
			password='not-a-real-password',
		)

	def cards_html(self):
		html = self.client.get('/subscription').content.decode()
		start = html.index('<div class="epic-cards">')
		end = html.index('</div>', html.index('Activate Enterprise Package')) + len('</div>')
		return html[start:end]

	def test_signed_out_visitors_see_the_plans_page_instead_of_the_login_page(self):
		response = self.client.get('/subscription')

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'subscription.html')

	def test_all_three_plans_and_their_prices_are_visible(self):
		response = self.client.get('/subscription')

		for expected in (
			'>Individual<', '>Family<', '>Enterprise<',
			'R49<span>/month</span>', 'R89<span>/month</span>',
			'For 1 child', 'For up to 4 children',
			'From</span> R20<span>/month per learner</span>',
			'Minimum 100 learners',
		):
			self.assertContains(response, expected)

	def test_the_full_enterprise_pricing_details_stay_open_to_everyone(self):
		body = self.client.get('/subscription').content.decode()

		self.assertIn('id="enterprise-pricing-dialog"', body)
		self.assertIn('National Master List of Schools', body)
		self.assertIn('pricing-table', body)

	def test_the_pricing_quote_endpoint_works_without_an_account(self):
		response = self.client.get(
			'/subscription/enterprise-pricing',
			{'school_type': 'quintile_1', 'learners': '100'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['total_month'], 'R4,000')

	def test_signed_out_visitors_cannot_submit_a_plan_choice(self):
		response = self.client.post('/subscription', {'plan': 'family'})
		self.assertRedirects(response, '/login', fetch_redirect_response=False)

	def test_the_trial_pitch_and_a_way_to_start_are_offered(self):
		response = self.client.get('/subscription')

		self.assertContains(response, '30-day free trial')
		self.assertContains(response, 'href="/register"')

	def test_no_plan_choosing_buttons_are_rendered_for_signed_out_visitors(self):
		body = self.client.get('/subscription').content.decode()
		cards = self.cards_html()

		self.assertNotIn('Choose Individual Plan', cards)
		self.assertNotIn('Choose Family Plan', cards)
		self.assertNotIn('name="plan"', cards)
		# ...and nothing that would post back here.
		self.assertNotIn('class="epic-skip"', body)

	def test_signed_in_visitors_keep_the_choosing_forms(self):
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = self.parent.id
		session.save()

		body = self.client.get('/subscription').content.decode()

		self.assertIn('Choose Individual Plan', body)
		self.assertIn('Choose Family Plan', body)
		self.assertIn('class="epic-skip"', body)

	def test_guest_cards_show_the_same_prices_as_a_signed_in_parent(self):
		guest_cards = self.cards_html()

		self.client = Client()
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = self.parent.id
		session.save()
		parent_cards = self.cards_html()

		for card in (guest_cards, parent_cards):
			self.assertIn('R49<span>/month</span>', card)
			self.assertIn('R89<span>/month</span>', card)
			self.assertIn('From</span> R20<span>/month per learner</span>', card)


class RedeemPackageHandoverTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.parent = Parent.objects.create(
			full_name='Handover Parent',
			email='handover-parent@example.com',
			password='not-a-real-password',
		)
		session = self.client.session
		session['account_role'] = 'parent'
		session['account_id'] = self.parent.id
		session.save()

	def test_school_type_and_learners_are_carried_into_activation(self):
		response = self.client.get(
			'/subscription/redeem-package',
			{'school_type': 'quintile_2', 'learners': '250'},
		)

		self.assertContains(response, 'Quintile 2')
		self.assertContains(response, '250 learners')
		self.assertContains(response, 'R8,750 per month')
		self.assertContains(response, 'name="school_type" value="quintile_2"')
		self.assertContains(response, 'name="learners" value="250"')

	def test_bad_handover_values_fall_back_to_sane_defaults(self):
		response = self.client.get(
			'/subscription/redeem-package',
			{'school_type': 'not-a-quintile', 'learners': '4'},
		)

		self.assertContains(response, '100 learners')

	def test_page_still_loads_with_no_handover_at_all(self):
		response = self.client.get('/subscription/redeem-package')

		self.assertContains(response, 'Activate school package')
		self.assertNotContains(response, 'Your estimate')