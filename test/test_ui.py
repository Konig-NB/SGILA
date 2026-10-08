import re

import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect
from api.models import (
    AIStoryJob,
    AccountActionOTP,
    Child,
    CauseEffectPair,
    Feedback,
    FeelingsQuestion,
    GradeHistory,
    HelpArticle,
    HelpCategory,
    InferenceQuestion,
    Lesson,
    OTPToken,
    PackageCode,
    Parent,
    PasswordResetToken,
    PredictionQuestion,
    Progress,
    ReadingActivity,
    SequencingActivity,
    StoryPage,
    SupportTicket,
    Subscription,
    ThemeQuestion,
    Teacher,
    VocabularyQuestion,
    VisualActivityItem,
    WrittenResponsePrompt,
    PronunciationWord,
    SpellingActivity,
)
from api.views import hash_password
from schools.models import School


@pytest.fixture(scope="session", autouse=True)
def allow_django_sync_calls_during_playwright():
    # Playwright's synchronous API owns an event loop. Keep Django's opt-in
    # setting in place through pytest-django's live-server database teardown.
    import os

    previous = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    yield
    if previous is None:
        os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
    else:
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous


@pytest.mark.django_db
def test_login_page_loads(django_db_setup, live_server, page: Page):
    page.goto(f"{live_server.url}{reverse('login-page')}")
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
    expect(page.get_by_role("button", name="Sign in")).to_be_visible()


def test_public_entry_pages_render(live_server, page: Page):
    """Smoke-check the public entry points used before account authentication."""
    paths = [
        "/",
        "/help/",
        "/terms",
        "/ui-flow",
        "/account-access?reason=parent_deactivated",
        "/register?role=parent",
        "/register?role=teacher",
        "/login?role=learner",
        "/login?role=parent",
        "/login?role=teacher",
        "/forgot-password?role=parent",
        "/plans",
    ]
    for path in paths:
        response = page.goto(f"{live_server.url}{path}")
        assert response is not None and response.status == 200, f"{path} returned {getattr(response, 'status', None)}"
        expect(page.locator("main").first).to_be_visible()


@pytest.mark.django_db
def test_parent_subscription_page_hides_add_seat_hint_and_keeps_controls(client):
    parent = Parent.objects.create(
        full_name="Subscription Parent",
        email="subscription-parent@example.test",
        password="test-password",
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="active")
    session = client.session
    session["account_role"] = "parent"
    session["account_id"] = parent.id
    session.save()

    response = client.get("/subscription")

    assert response.status_code == 200
    assert b"Already on a plan and need more active learners?" not in response.content
    assert b"Add a seat" not in response.content
    assert b"Choose Individual Plan" in response.content
    assert b"Choose Family Plan" in response.content
    assert b"Cancel subscription" in response.content


def test_ui_flow_downloads_pdf(live_server, page: Page):
    page.goto(f"{live_server.url}/ui-flow")
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Download readable PDF").click()
    download = download_info.value
    assert download.suggested_filename.endswith(".pdf")


@pytest.mark.django_db(transaction=True)
def test_help_search_support_ticket_and_feedback(live_server, page: Page):
    category = HelpCategory.objects.create(name="Accounts", slug="accounts", order=1)
    HelpArticle.objects.create(
        category=category,
        title="Reset a learner password",
        slug="reset-learner-password",
        audience=HelpArticle.Audience.PARENT,
        content="Use the parent dashboard to help your learner reset a password.",
    )
    page.goto(f"{live_server.url}/help/")
    page.get_by_label("How can we help you?").fill("learner password")
    expect(page.get_by_text("Reset a learner password")).to_be_visible()

    page.locator("#contact summary").click()
    page.locator("#ticket-email").fill("help@example.test")
    page.locator("#ticket-subject").fill("Can't sign in")
    page.locator("#ticket-description").fill("The learner password reset did not work.")
    page.get_by_role("button", name="Send message").click()
    expect(page.get_by_text("Your message was sent to SGILA support.", exact=False)).to_be_visible()
    assert SupportTicket.objects.filter(email="help@example.test", subject="Can't sign in").exists()

    page.locator("#feedback summary").click()
    page.locator("#feedback-email").fill("feedback@example.test")
    page.get_by_label("Your role").select_option("parent")
    page.get_by_label("Feedback type").select_option("suggestion")
    page.locator("#feedback-subject").fill("More stories")
    page.locator("#feedback-message").fill("Please add more stories for younger learners.")
    page.get_by_role("button", name="Send feedback").click()
    expect(page.get_by_text("Feedback #", exact=False)).to_be_visible()
    assert Feedback.objects.filter(user_email="feedback@example.test", issue_category="suggestion").exists()


@pytest.mark.django_db(transaction=True)
def test_parent_can_sign_in_and_invalid_password_is_rejected(live_server, page: Page):
    Parent.objects.create(
        full_name="Playwright Parent",
        email="playwright-parent@example.test",
        password=hash_password("correct-horse-battery"),
    )

    page.goto(f"{live_server.url}/login?role=parent")
    page.get_by_label("Email").fill("playwright-parent@example.test")
    page.get_by_label("Password").fill("wrong-password")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/login")
    expect(page.get_by_role("heading", name="Parent login")).to_be_visible()
    expect(page.get_by_label("Password")).to_be_visible()

    page.get_by_label("Email").fill("playwright-parent@example.test")
    page.get_by_label("Password").fill("correct-horse-battery")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    expect(page.locator("body")).to_contain_text("Dashboard")


@pytest.mark.django_db(transaction=True)
def test_parent_trial_child_learning_and_ai_story_journey(live_server, page: Page, monkeypatch):
    """Exercise signup, verification, trial, child creation, learning and AI story UI."""
    import lessons.views as lesson_views

    page.goto(f"{live_server.url}/register?role=parent")
    page.get_by_label("Full name").fill("Playwright Family")
    page.get_by_label("Email", exact=True).fill("family-flow@example.test")
    page.get_by_label("Phone").fill("0712345678")
    page.locator("#password").fill("Correct-Horse-42!")
    page.get_by_label("I accept SGILA's terms and conditions.").check()
    page.get_by_role("button", name="Create parent account").click()
    expect(page.get_by_role("heading", name="Check your email")).to_be_visible()

    otp = OTPToken.objects.get(email="family-flow@example.test", role="parent", is_used=False)
    for index, digit in enumerate(otp.code):
        page.get_by_label(f"Digit {index + 1}").fill(digit)
    page.get_by_role("button", name="Verify & continue").click()
    expect(page.get_by_role("heading", name="Hi Playwright Family, you're all set!")).to_be_visible()

    parent = Parent.objects.get(email="family-flow@example.test")
    subscription = Subscription.objects.get(parent=parent)
    assert subscription.plan_type == "family"
    assert subscription.status == "trial"
    expect(page.get_by_text("Free 30-day trial")).to_be_visible()
    page.get_by_role("link", name="Go to my dashboard").click()
    expect(page.get_by_role("heading", name="Hello, Playwright Family!")).to_be_visible()
    expect(page.get_by_text("Free trial - Family plan")).to_be_visible()

    page.get_by_role("main").get_by_role("link", name="Add child").click()
    page.get_by_label("Username").fill("Mila")
    page.get_by_label("First name").fill("Mila")
    page.get_by_label("Last name").fill("Tester")
    page.get_by_label("Date of birth").fill("2018-05-12")
    page.get_by_label("Grade").select_option("1")
    page.get_by_label("Learner password").fill("Learner-pass-42!")
    page.get_by_role("button", name="Add learner").click()
    expect(page.get_by_text("Mila Tester")).to_be_visible()

    child = parent.children.get(username__iexact="mila")
    lesson = Lesson.objects.create(title="Mila's First Story", grade=1)
    StoryPage.objects.create(lesson=lesson, page_number=1, text="Mila found a red kite in the garden.")
    StoryPage.objects.create(lesson=lesson, page_number=2, text="She flew it high above the trees.")
    ReadingActivity.objects.create(
        lesson=lesson,
        activity_type=ReadingActivity.MULTIPLE_CHOICE,
        skill="literal_comprehension",
        question="What did Mila find?",
        options=["A red kite", "A blue ball"],
        correct_answer="A red kite",
        group_number=2,
        group_title="Remember the story",
        order=1,
    )

    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=learner")
    page.get_by_label("Username").fill("Mila")
    page.get_by_label("Password").fill("Learner-pass-42!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/grade/1")
    expect(page.get_by_role("heading", name="Hey, Mila Tester!")).to_be_visible()

    page.get_by_role("link", name="Mila's First Story").click()
    page.get_by_role("dialog").get_by_role("link", name="Read the Story").click()
    expect(page.get_by_text("Mila found a red kite in the garden.")).to_be_visible()
    page.get_by_role("button", name="Next").click()
    page.get_by_role("link", name="Start 3 activities").click()
    expect(page.get_by_role("heading", name="Mila's First Story")).to_be_visible()
    expect(page.get_by_role("button", name="A red kite")).to_be_visible()
    page.get_by_role("button", name="A red kite").click()
    page.get_by_role("button", name="Check answer").click()
    expect(page.get_by_text("Correct", exact=True)).to_be_visible()
    page.get_by_role("button", name="Finish activities").click()
    expect(page.get_by_role("heading", name="Amazing work, Mila Tester!")).to_be_visible()
    assert Progress.objects.filter(child=child, lesson=lesson).exists()

    # Replace the external provider/background worker with a completed job while
    # keeping the real browser POST, status polling, and ready-story navigation.
    generated_lesson = Lesson.objects.create(
        title="Mila's AI Garden Adventure", grade=1, is_ai_generated=True, generated_for=child,
    )
    StoryPage.objects.create(lesson=generated_lesson, page_number=1, text="Mila's kite led her to a secret garden.")
    monkeypatch.setattr(lesson_views, "story_text_provider_configured", lambda grade: True)

    def completed_ai_job(target_child, grade):
        return AIStoryJob.objects.create(
            child=target_child, grade=grade, status=AIStoryJob.STATUS_DONE, lesson=generated_lesson,
        )

    monkeypatch.setattr(lesson_views, "start_ai_story_job", completed_ai_job)
    page.goto(f"{live_server.url}/grade/1")
    page.get_by_role("button", name="Explore more stories").click()
    expect(page.get_by_text("Your story is ready!")).to_be_visible(timeout=10000)
    page.get_by_role("button", name="Read your new story").click()
    expect(page).to_have_url(f"{live_server.url}/lessons/{generated_lesson.id}/story")
    expect(page.get_by_text("Mila's kite led her to a secret garden.")).to_be_visible()

    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=parent")
    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("Correct-Horse-42!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    expect(page.get_by_text("Mila Tester")).to_be_visible()
    expect(page.get_by_text("1/2 lessons done")).to_be_visible()

    page.get_by_role("link", name="Report").click()
    expect(page.get_by_role("heading", name="Mila Tester's story progress")).to_be_visible()
    page.goto(f"{live_server.url}/dashboard/{child.id}/lessons/{lesson.id}")
    expect(page.get_by_role("heading", name="Mila's First Story")).to_be_visible()

    child.grade_confirmed_year = 2025
    child.save(update_fields=["grade_confirmed_year"])
    page.goto(f"{live_server.url}/parent/dashboard")
    expect(page.get_by_text("New school year: please confirm each child's grade")).to_be_visible()
    page.get_by_role("button", name="Move up to Grade 2").click()
    page.locator("#grade-confirm-continue").click()
    child.refresh_from_db()
    assert child.grade == 2
    assert child.grade_confirmed_year == 2026
    assert GradeHistory.objects.filter(child=child, year=2026, grade=2).exists()

    page.goto(f"{live_server.url}/dashboard/{child.id}")
    page.get_by_role("button", name="Deactivate learner").click()
    page.get_by_role("dialog").get_by_role("button", name="Continue").click()
    expect(page.get_by_role("button", name="Reactivate learner")).to_be_visible()
    page.get_by_role("button", name="Reactivate learner").click()
    page.get_by_role("dialog").get_by_role("button", name="Continue").click()
    expect(page.get_by_role("button", name="Deactivate learner")).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_parent_password_recovery_and_new_password_login(live_server, page: Page, monkeypatch):
    School.objects.create(
        emis_number="PW-ENT-001",
        name="Playwright Primary School",
        province="Gauteng",
        quintile=3,
        sector="public",
        learners_2025=120,
        status="open",
    )
    parent = Parent.objects.create(
        full_name="Recovery Parent",
        email="recovery@example.test",
        password=hash_password("Old-Password-42!"),
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="trial")

    page.goto(f"{live_server.url}/forgot-password?role=parent")
    page.get_by_label("Email").fill(parent.email)
    page.get_by_role("button", name="Send reset link").click()
    expect(page.get_by_role("heading", name="Check your inbox")).to_be_visible()
    token = PasswordResetToken.objects.get(email=parent.email, role="parent", is_used=False)

    page.goto(f"{live_server.url}/reset-password?token={token.token}&role=parent")
    page.get_by_label("New password").fill("New-Password-52!")
    page.get_by_label("Confirm password").fill("New-Password-52!")
    page.get_by_role("button", name="Set new password").click()
    expect(page).to_have_url(f"{live_server.url}/login?role=parent")
    assert PasswordResetToken.objects.get(pk=token.pk).is_used

    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("New-Password-52!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")

    page.get_by_role("link", name="Plan", exact=True).click()
    page.get_by_role("button", name="Choose Family Plan").click()
    expect(page).to_have_url(f"{live_server.url}/subscription/payment")
    page.get_by_label("Name on card").fill("Recovery Parent")
    page.get_by_label("Card number").fill("4111111111111111")
    page.get_by_label("Expiry (MM/YYYY)").fill("08/2028")
    page.get_by_label("CVV").fill("123")
    page.get_by_role("button", name="Confirm and go to my dashboard").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    subscription = Subscription.objects.get(parent=parent)
    assert subscription.status == "active"
    assert subscription.card_last4 == "1111"

    page.goto(f"{live_server.url}/subscription/add-seat")
    page.get_by_label("Number of extra seats").fill("2")
    page.get_by_role("button", name="Continue to payment").click()
    expect(page.get_by_role("heading", name="Confirm your extra seats")).to_be_visible()
    page.get_by_role("button", name="Use a different payment method").click()
    page.get_by_role("link", name="Bank debit order").click()
    page.get_by_label("Account holder name").fill("Recovery Parent")
    page.get_by_label("Bank name").fill("Test Bank")
    page.get_by_label("Account number").fill("1234567890")
    page.get_by_label("Branch code").fill("123456")
    page.get_by_role("button", name="Confirm and add 2 seats").click()
    subscription.refresh_from_db()
    assert subscription.extra_active_seats == 2
    assert subscription.payment_method == "debit_order"
    assert subscription.account_last4 == "7890"

    package_code = PackageCode.objects.create(code="PLAYWRIGHT-ENTERPRISE", label="Playwright test")
    page.goto(f"{live_server.url}/subscription")
    page.get_by_role("button", name="See full pricing details").click()
    expect(page.get_by_role("dialog").get_by_role("heading", name="Full school pricing details")).to_be_visible()
    finder = page.locator("#enterprise-pricing-dialog")
    finder.locator("[data-sf-province]").select_option("Gauteng")
    finder.locator("[data-sf-query]").fill("Playwright Primary")
    school_option = finder.locator('[data-sf-suggestions] [role="option"]')
    expect(school_option).to_be_visible()
    school_option.click()
    expect(finder.locator("[data-sf-selected-name]")).to_contain_text("Playwright Primary School")
    expect(page.locator("[data-pricing-activate]")).to_have_attribute("href", re.compile(r"school_id=\d+"))
    page.locator("[data-pricing-activate]").click()
    expect(page).to_have_url(re.compile(r"/subscription/redeem-package\?.*school_id=\d+.*learners=120.*school_type=quintile_3"))
    expect(page.locator('input[name="school_name"]')).to_have_value("Playwright Primary School")
    page.get_by_label("Package code").fill(package_code.code)
    page.get_by_role("button", name="Activate school package").click()
    subscription.refresh_from_db()
    package_code.refresh_from_db()
    assert subscription.plan_type == "enterprise"
    assert subscription.status == "active"
    assert package_code.redemptions_count == 1

    page.goto(f"{live_server.url}/subscription/cancel")
    page.get_by_role("button", name="Yes — cancel my subscription").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    subscription.refresh_from_db()
    assert subscription.status == "cancelled"

    import lessons.views as lesson_views

    sent_messages = []
    monkeypatch.setattr(
        lesson_views,
        "send_mail",
        lambda subject, message, *args, **kwargs: sent_messages.append(message) or 1,
    )
    page.locator("#open-deactivate-dialog").click()
    page.locator('#deactivate-dialog input[name="password"]').fill("New-Password-52!")
    page.locator('#deactivate-dialog button[type="submit"]').click()
    parent.refresh_from_db()
    assert not parent.is_active
    expect(page).to_have_url(f"{live_server.url}/login?role=parent")

    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("New-Password-52!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/account/reactivate")
    page.get_by_role("button", name="Yes, send reactivation code").click()
    expect(page.get_by_label("Reactivation code")).to_be_visible()
    code_match = re.search(r"reactivation code is: (\d{6})", sent_messages[-1], re.IGNORECASE)
    assert code_match, "The reactivation email should contain its six-digit code."
    page.get_by_label("Reactivation code").fill(code_match.group(1))
    page.get_by_role("button", name="Verify and reactivate").click()
    parent.refresh_from_db()
    assert parent.is_active
    expect(page).to_have_url(f"{live_server.url}/subscription")
    assert AccountActionOTP.objects.filter(parent=parent, is_used=True).exists()


@pytest.mark.django_db(transaction=True)
def test_enterprise_package_redemption_and_cancellation(live_server, page: Page):
    """Exercise redemption independently from the pricing dialog hand-off."""
    parent = Parent.objects.create(
        full_name="Package Parent",
        email="package-parent@example.test",
        password=hash_password("Package-Pass-42!"),
    )
    subscription = Subscription.objects.create(parent=parent, plan_type="family", status="trial")
    package_code = PackageCode.objects.create(code="PACKAGE-FLOW-001", label="Playwright package")

    page.goto(f"{live_server.url}/login?role=parent")
    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("Package-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/subscription/redeem-package")
    page.locator('input[name="school_name"]').fill("Manual Playwright School")
    page.get_by_label("Package code").fill(package_code.code)
    page.get_by_role("button", name="Activate school package").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    subscription.refresh_from_db()
    package_code.refresh_from_db()
    assert subscription.plan_type == "enterprise"
    assert subscription.status == "active"
    assert subscription.school_name == "Manual Playwright School"
    assert package_code.redemptions_count == 1

    page.goto(f"{live_server.url}/subscription/cancel")
    page.get_by_role("button", name="Yes — cancel my subscription").click()
    expect(page).to_have_url(f"{live_server.url}/parent/dashboard")
    subscription.refresh_from_db()
    assert subscription.status == "cancelled"


@pytest.mark.django_db(transaction=True)
def test_grade_four_activity_interactions_and_results(live_server, page: Page):
    """Complete each Grade 4 activity UI and submit a written response."""
    parent = Parent.objects.create(
        full_name="Grade Four Parent",
        email="grade-four-parent@example.test",
        password=hash_password("Parent-Pass-42!"),
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="trial")
    child = Child.objects.create(
        parent=parent,
        username="GradeFourLearner",
        first_name="Grade Four",
        last_name="Learner",
        name="Grade Four Learner",
        grade=4,
        parent_email=parent.email,
        password=hash_password("Learner-Pass-42!"),
    )
    lesson = Lesson.objects.create(title="Grade Four Practice", grade=4)
    StoryPage.objects.create(lesson=lesson, page_number=1, text="The learner solves a puzzle.")
    VocabularyQuestion.objects.create(
        lesson=lesson, word="brave", option_1="courageous", option_2="sleepy",
        option_3="tiny", correct_answer="courageous",
    )
    SequencingActivity.objects.create(lesson=lesson, ordered_events="Wake up|Walk to school")
    InferenceQuestion.objects.create(
        lesson=lesson, question="How did the learner feel?", option_1="Happy",
        option_2="Sad", option_3="Angry", option_4="Tired", correct_answer="Happy",
    )
    PredictionQuestion.objects.create(
        lesson=lesson, stop_point_text="The learner picked up an umbrella.",
        question="What might happen next?", option_1="It may rain", option_2="It is bedtime",
        option_3="They will swim", option_4="They will cook", correct_answer="It may rain",
    )
    FeelingsQuestion.objects.create(
        lesson=lesson, question="How does a friend feel after being helped?",
        option_1="Grateful", option_2="Upset", option_3="Confused", option_4="Bored",
        correct_answer="Grateful",
    )
    CauseEffectPair.objects.create(lesson=lesson, cause="It rained", effect="The ground got wet")
    ThemeQuestion.objects.create(
        lesson=lesson, question="What is the lesson?", option_1="Help others",
        option_2="Ignore friends", option_3="Avoid learning", option_4="Never share",
        correct_answer="Help others",
    )
    WrittenResponsePrompt.objects.create(lesson=lesson, prompt="How did the learner solve the problem?")

    page.goto(f"{live_server.url}/login?role=learner")
    page.get_by_label("Username").fill(child.username)
    page.get_by_label("Password").fill("Learner-Pass-42!")
    page.get_by_role("button", name="Sign in").click()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/vocabulary")
    page.get_by_role("button", name="Take a break").first.click()
    page.get_by_role("dialog").get_by_role("button", name="Take a break").click()
    expect(page.get_by_role("dialog").get_by_role("heading", name="Which activity do you want to start with?")).to_be_visible()
    resume_link = page.get_by_role("link", name="Continue where I paused")
    expect(resume_link).to_be_visible()
    resume_link.click()
    expect(page).to_have_url(f"{live_server.url}/lessons/{lesson.id}/vocabulary")

    page.goto(f"{live_server.url}/lessons/{lesson.id}/vocabulary")
    page.get_by_role("button", name="courageous").click()
    expect(page.get_by_text("Correct! Well done!")).to_be_visible()
    page.get_by_role("button", name="Finish vocabulary").click()
    expect(page.get_by_text("Well done! You matched all the words.")).to_be_visible()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/sequencing")
    events = page.locator("#event-list li")
    expect(events).to_have_count(2)
    correct_order = ["Wake up", "Walk to school"]
    for index, expected in enumerate(correct_order):
        source = page.locator("#event-list li").filter(has_text=expected)
        target = page.locator("#event-list li").nth(index)
        if source.count() and source.first.evaluate("(el, target) => el !== target", target.element_handle()):
            source.first.drag_to(target)
    page.get_by_role("button", name="Check my order").click()
    expect(page.get_by_text("Perfect order! Well done!")).to_be_visible()

    for route, question, answer, next_button in [
        ("inference", "How did the learner feel?", "Happy", "Finish inference"),
        ("feelings", "How does a friend feel after being helped?", "Grateful", "Finish feelings"),
    ]:
        page.goto(f"{live_server.url}/lessons/{lesson.id}/{route}")
        expect(page.get_by_text(question)).to_be_visible()
        page.get_by_role("button", name=answer).click()
        expect(page.locator("#message-area")).to_contain_text("Correct!")
        page.get_by_role("button", name=next_button).click()
        expect(page.locator("#results-area")).to_be_visible()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/prediction")
    page.get_by_role("button", name="It may rain").click()
    expect(page.locator("#message-area")).to_contain_text("Correct!")
    expect(page.locator("#results-area")).to_be_visible()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/cause-effect")
    page.locator(".cause-card").first.click()
    page.locator(".effect-card").first.click()
    page.get_by_role("button", name="Check my matches").click()
    expect(page.get_by_text("Perfect! All 1 matches are correct!")).to_be_visible()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/theme")
    page.get_by_role("button", name="Help others").click()
    expect(page.locator("#message-area")).to_contain_text("Correct!")
    page.get_by_role("link", name="Submit and see my results").click()
    expect(page).to_have_url(f"{live_server.url}/lessons/{lesson.id}/results")

    page.goto(f"{live_server.url}/lessons/{lesson.id}/written-response")
    page.locator('textarea[name="response_text"]').fill("The learner asked for help and solved the puzzle.")
    page.get_by_role("button", name="Submit and see my results").click()
    expect(page).to_have_url(f"{live_server.url}/lessons/{lesson.id}/results")
    assert Progress.objects.filter(child=child, lesson=lesson).exists()


@pytest.mark.django_db(transaction=True)
def test_visual_pronunciation_and_all_spelling_types(live_server, page: Page):
    parent = Parent.objects.create(
        full_name="Phonics Parent",
        email="phonics-parent@example.test",
        password=hash_password("Parent-Pass-42!"),
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="trial")
    child = Child.objects.create(
        parent=parent,
        username="PhonicsLearner",
        first_name="Phonics",
        last_name="Learner",
        name="Phonics Learner",
        grade=1,
        parent_email=parent.email,
        password=hash_password("Learner-Pass-42!"),
    )
    lesson = Lesson.objects.create(title="Phonics Practice", grade=1)
    VisualActivityItem.objects.create(
        lesson=lesson, correct_word="Apple", word_options="Apple,Banana,Orange",
    )
    PronunciationWord.objects.create(
        lesson=lesson, word="apple", isizulu_word="ihhabhula",
    )
    spelling_items = [
        (SpellingActivity.FILL_VOWEL, "Appl_", "Apple"),
        (SpellingActivity.DRAG_LETTERS, "A,P,P,L,E", "APPLE"),
        (SpellingActivity.COPY_WRITING, "Apple", "Apple"),
    ]
    for activity_type, display_text, answer in spelling_items:
        SpellingActivity.objects.create(
            lesson=lesson,
            activity_type=activity_type,
            display_text=display_text,
            answer=answer,
        )

    page.goto(f"{live_server.url}/login?role=learner")
    page.get_by_label("Username").fill(child.username)
    page.get_by_label("Password").fill("Learner-Pass-42!")
    page.get_by_role("button", name="Sign in").click()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/visual-activity")
    page.locator(".activity-card").get_by_role("button", name="Apple").click()
    expect(page.get_by_text("Finished! You matched 1 of 1.")).to_be_visible()
    page.get_by_role("link", name="Continue").click()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/pronunciation")
    page.evaluate("""() => {
      Object.defineProperty(window, 'SpeechSynthesisUtterance', {
        configurable: true,
        value: function (text) { this.text = text; }
      });
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [{name: 'Test English Voice', lang: 'en-ZA'}],
        addEventListener: () => {}, cancel: () => {}, resume: () => {},
        speak: (utterance) => { utterance.onstart?.(); utterance.onend?.(); },
        speaking: false, pending: false
      }});
    }
    """)
    page.get_by_role("button", name="English").click()
    expect(page.get_by_role("button", name="Replay English")).to_be_visible()
    expect(page.get_by_role("status")).to_contain_text("English: apple")
    page.get_by_role("button", name="isiZulu").click()
    expect(page.get_by_role("button", name="Replay isiZulu")).to_be_visible()

    page.goto(f"{live_server.url}/lessons/{lesson.id}/spelling")
    for activity_type, _display_text, answer in spelling_items:
        card = page.locator(f'.spelling-card[data-activity-type="{activity_type}"]')
        card.locator("input").fill(answer)
        card.get_by_role("button", name="Check answer").click()
        expect(card.locator(".spelling-feedback")).to_contain_text("Correct!")
    page.get_by_role("button", name="Finish lesson").click()
    expect(page).to_have_url(f"{live_server.url}/lessons/{lesson.id}/results")


@pytest.mark.django_db(transaction=True)
def test_all_grade_lesson_and_activity_screens_render_for_the_matching_learner(live_server, page: Page):
    """Walk every learner lesson/activity page family with a grade-matched login."""
    parent = Parent.objects.create(
        full_name="Curriculum Parent",
        email="curriculum-parent@example.test",
        password=hash_password("Parent-Pass-42!"),
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="trial")

    for grade in range(1, 5):
        username = f"Grade{grade}Learner"
        child = Child.objects.create(
            parent=parent,
            username=username,
            first_name=f"Grade {grade}",
            last_name="Learner",
            name=f"Grade {grade} Learner",
            grade=grade,
            parent_email=parent.email,
            password=hash_password("Learner-Pass-42!"),
        )
        lesson = Lesson.objects.create(title=f"Grade {grade} Story", grade=grade)
        StoryPage.objects.create(lesson=lesson, page_number=1, text=f"A practice story for Grade {grade}.")
        Progress.objects.create(child=child, lesson=lesson, total_score=1, total_possible=1, stars_earned=1)

        page.goto(f"{live_server.url}/login?role=learner")
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill("Learner-Pass-42!")
        page.get_by_role("button", name="Sign in").click()
        expect(page).to_have_url(f"{live_server.url}/grade/{grade}")
        expect(page.get_by_role("heading", name=f"Hey, Grade {grade} Learner!")).to_be_visible()

        grade_paths = [
            f"/grade/{grade}",
            f"/lessons/{lesson.id}/story",
            f"/lessons/{lesson.id}/questions",
            f"/lessons/{lesson.id}/visual-activity",
            f"/lessons/{lesson.id}/pronunciation",
            f"/lessons/{lesson.id}/spelling",
            f"/lessons/{lesson.id}/results",
            f"/dashboard/{child.id}",
        ]
        if grade == 3:
            grade_paths.extend([
                f"/lessons/{lesson.id}/activities",
            ])
        if grade == 4:
            grade_paths.extend([
                f"/lessons/{lesson.id}/vocabulary",
                f"/lessons/{lesson.id}/sequencing",
                f"/lessons/{lesson.id}/inference",
                f"/lessons/{lesson.id}/prediction",
                f"/lessons/{lesson.id}/feelings",
                f"/lessons/{lesson.id}/cause-effect",
                f"/lessons/{lesson.id}/theme",
                f"/lessons/{lesson.id}/written-response",
            ])
        for path in grade_paths:
            response = page.goto(f"{live_server.url}{path}")
            assert response is not None and response.status == 200, (
                f"Grade {grade} learner route {path} returned {getattr(response, 'status', None)}"
            )
            expect(page.locator("main").first).to_be_visible()

        if grade == 3:
            page.goto(f"{live_server.url}/lessons/{lesson.id}/activities")
            expect(page.get_by_role("heading", name="Activity 1")).to_be_visible()
            question = page.locator(".grade3-question-card").first
            expect(question).to_be_visible()
            question.locator(".text-option").first.click()
            question.get_by_role("button", name="Check answer").click()
            expect(question.locator(".answer-review")).to_be_visible()
            completion = page.evaluate(
                """async (path) => {
                  const csrf = decodeURIComponent((document.cookie.match(/(?:^|; )csrftoken=([^;]*)/) || [])[1] || '');
                  const response = await fetch(path, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                    body: JSON.stringify({activity_scores: [
                      {number: 1, score: 1, total: 1},
                      {number: 2, score: 1, total: 1},
                      {number: 3, score: 1, total: 1},
                      {number: 4, score: 1, total: 1},
                      {number: 5, score: 1, total: 1},
                      {number: 6, score: 1, total: 1}
                    ]})
                  });
                  return {status: response.status, body: await response.json()};
                }""",
                f"/lessons/{lesson.id}/activities/complete",
            )
            assert completion == {"status": 200, "body": {"completed": True}}
            grade3_progress = Progress.objects.get(child=child, lesson=lesson)
            assert grade3_progress.total_score == 6
            assert grade3_progress.total_possible == 6

        page.goto(f"{live_server.url}/logout")


@pytest.mark.django_db(transaction=True)
def test_teacher_signup_verification_trial_and_dashboard(live_server, page: Page, monkeypatch):
    School.objects.create(
        emis_number="PW-001",
        name="Sample Primary School",
        province="Gauteng",
        quintile=3,
        sector="public",
        learners_2025=120,
        status="open",
    )
    page.goto(f"{live_server.url}/register?role=teacher")
    page.get_by_label("Full name").fill("Playwright Teacher")
    page.get_by_label("Work email").fill("teacher-flow@example.test")
    page.get_by_label("School name").fill("Sample Primary School")
    page.get_by_label("Grades taught").fill("1, 2")
    page.locator("#password").fill("Teacher-Pass-42!")
    page.get_by_label("I accept SGILA's terms and conditions.").check()
    page.get_by_role("button", name="Create teacher account").click()
    expect(page.get_by_role("heading", name="Check your email")).to_be_visible()

    otp = OTPToken.objects.get(email="teacher-flow@example.test", role="teacher", is_used=False)
    for index, digit in enumerate(otp.code):
        page.get_by_label(f"Digit {index + 1}").fill(digit)
    page.get_by_role("button", name="Verify & continue").click()
    expect(page).to_have_url(f"{live_server.url}/teacher/dashboard")
    expect(page.get_by_role("heading", name="Hello, Playwright Teacher")).to_be_visible()

    teacher = Teacher.objects.get(email="teacher-flow@example.test")
    assert teacher.school_name == "Sample Primary School"
    assert teacher.class_code
    assert teacher.classes.exists()
    expect(page.get_by_text(teacher.class_code, exact=True)).to_be_visible()
    expect(page.get_by_text("No learners found yet.")).to_be_visible()

    page.get_by_role("link", name="Plan").click()
    expect(page.get_by_text("All teacher plans include a 30-day trial")).to_be_visible()
    assert Subscription.objects.filter(teacher=teacher, status="trial").exists()

    # Follow the teacher's shared code through the parent add-child flow, then
    # confirm the learner and report appear to the teacher.
    parent = Parent.objects.create(
        full_name="Linked Parent",
        email="linked-parent@example.test",
        password=hash_password("Parent-Pass-42!"),
    )
    Subscription.objects.create(parent=parent, plan_type="family", status="trial")
    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=parent")
    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("Parent-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_role("main").get_by_role("link", name="Add child").click()
    page.get_by_label("Username").fill("Ayo")
    page.get_by_label("First name").fill("Ayo")
    page.get_by_label("Last name").fill("Learner")
    page.get_by_label("Date of birth").fill("2018-05-12")
    page.get_by_label("Grade").select_option("1")
    page.get_by_label("Class code").fill(teacher.class_code)
    page.get_by_label("Learner password").fill("Learner-Pass-42!")
    page.get_by_role("button", name="Add learner").click()
    linked_child = Child.objects.get(username="Ayo")
    assert linked_child.teacher_id == teacher.id

    page.get_by_role("link", name="Messages").click()
    expect(page.get_by_role("heading", name="Messages")).to_be_visible()
    page.get_by_role("link", name="Ayo Learner").click()
    page.locator("#chat-input").fill("Ayo enjoyed today's reading lesson.")
    page.get_by_role("button", name="Send").click()
    expect(page.get_by_text("Ayo enjoyed today's reading lesson.")).to_be_visible()

    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=teacher")
    page.get_by_label("Email").fill(teacher.email)
    page.get_by_label("Password").fill("Teacher-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_role("heading", name="Hello, Playwright Teacher")).to_be_visible()
    expect(page.get_by_role("heading", name="Ayo Learner")).to_be_visible()
    page.get_by_role("link", name="Messages").click()
    page.get_by_role("link", name="Ayo Learner").click()
    expect(page.get_by_text("Ayo enjoyed today's reading lesson.")).to_be_visible()
    page.locator("#chat-input").fill("Thanks for letting me know!")
    page.get_by_role("button", name="Send").click()
    expect(page.get_by_text("Thanks for letting me know!")).to_be_visible()

    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=parent")
    page.get_by_label("Email").fill(parent.email)
    page.get_by_label("Password").fill("Parent-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_role("link", name="Messages").click()
    page.get_by_role("link", name="Ayo Learner").click()
    expect(page.get_by_text("Thanks for letting me know!")).to_be_visible()

    page.goto(f"{live_server.url}/logout")
    page.goto(f"{live_server.url}/login?role=teacher")
    page.get_by_label("Email").fill(teacher.email)
    page.get_by_label("Password").fill("Teacher-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_role("heading", name="Hello, Playwright Teacher")).to_be_visible()
    page.get_by_role("link", name="Report").click()
    expect(page).to_have_url(f"{live_server.url}/dashboard/{linked_child.id}")
    expect(page.get_by_role("heading", name="Ayo Learner's story progress")).to_be_visible()

    page.goto(f"{live_server.url}/teacher/dashboard")
    import lessons.views as lesson_views

    sent_messages = []
    monkeypatch.setattr(
        lesson_views,
        "send_mail",
        lambda subject, message, *args, **kwargs: sent_messages.append(message) or 1,
    )
    page.locator("#open-deactivate-dialog").click()
    page.locator('#deactivate-dialog input[name="password"]').fill("Teacher-Pass-42!")
    page.locator('#deactivate-dialog button[type="submit"]').click()
    teacher.refresh_from_db()
    assert not teacher.is_active
    assert teacher.classes.filter(needs_new_teacher=True).exists()

    page.get_by_label("Email").fill(teacher.email)
    page.get_by_label("Password").fill("Teacher-Pass-42!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{live_server.url}/account/reactivate")
    page.get_by_role("button", name="Yes, send reactivation code").click()
    code_match = re.search(r"reactivation code is: (\d{6})", sent_messages[-1], re.IGNORECASE)
    assert code_match, "The teacher reactivation email should contain a six-digit code."
    page.get_by_label("Reactivation code").fill(code_match.group(1))
    page.get_by_role("button", name="Verify and reactivate").click()
    teacher.refresh_from_db()
    assert teacher.is_active
    assert not teacher.classes.filter(needs_new_teacher=True).exists()
    assert AccountActionOTP.objects.filter(teacher=teacher, is_used=True).exists()
    expect(page).to_have_url(f"{live_server.url}/teacher/dashboard")
