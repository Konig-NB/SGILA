"""
SGILA API VIEWS
Each function below matches exactly one endpoint from the API contract.
Read the docstring at the top of each view to understand what screen it serves.
"""
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .validators import password_strength_errors
from .validators import password_strength_errors
from django.contrib.auth.hashers import check_password, make_password
import json
import hashlib
import re
import csv
from functools import lru_cache

import logging
import threading
from datetime import timedelta
from typing import Tuple


from django.utils import timezone
from api.models import AIStoryJob, Child, Lesson
from api.grade4_story_framework import (
    are_story_thresholds_enabled,
    retrieve_grade4_context,
    grade4_prompt_context,
    call_gemini_for_story,
    validate_and_repair_grade4_story,
    save_grade4_lesson,
)
from api.story_eligibility import check_ai_story_eligibility

logger = logging.getLogger(__name__)



import random
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone

import secrets
from .models import (
    CauseEffectPair,
    Child, Parent, Teacher, Lesson, StoryPage, ComprehensionQuestion,
    ReadingActivity, ReadingActivityResponse,
    FeelingsQuestion,
    InferenceQuestion,
    PredictionQuestion,
    SequencingActivity,
    ThemeQuestion,
    VocabularyQuestion,
    VisualActivityItem, PronunciationWord, SpellingActivity, Progress,
    WrittenResponsePrompt,
    OTPToken, PasswordResetToken,
    Message,
    Subscription,
    title_case,
)
from .account_access import child_access_status, linked_parent_for_child
from .jwt_utils import create_access_token, token_from_request
from .reporting import rows_for_record


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def json_body(request):
    """Parse JSON from the request body. Returns a dict."""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


@lru_cache(maxsize=1)
def school_directory_records():
    """Load only the sanitized public fields needed by teacher registration."""
    directory_path = django_settings.BASE_DIR / 'static' / 'data' / 'national_schools.csv'
    if not directory_path.is_file():
        return ()

    with directory_path.open(encoding='utf-8-sig', newline='') as directory_file:
        return tuple(
            {
                'school_name': row['school_name'].strip(),
                'location': (
                    '' if row['location'].strip().upper() in {'99', 'UNKNOWN', 'NULL', 'N/A'}
                    else row['location'].strip()
                ),
                'quantile': row['quantile'].strip(),
            }
            for row in csv.DictReader(directory_file)
            if row.get('school_name', '').strip()
        )


@require_http_methods(['GET'])
def school_search(request):
    query = request.GET.get('q', '').strip()[:100].casefold()
    if len(query) < 2:
        return JsonResponse({'results': []})

    matches = []
    for school in school_directory_records():
        normalized_name = school['school_name'].casefold()
        normalized_location = school['location'].casefold()
        if query in normalized_name or query in normalized_location:
            name_rank = 0 if normalized_name.startswith(query) else 1
            matches.append((name_rank, school))

    matches.sort(key=lambda match: (
        match[0],
        match[1]['school_name'].casefold(),
        match[1]['location'].casefold(),
        match[1]['quantile'],
    ))
    return JsonResponse({'results': [school for _rank, school in matches[:12]]})


def calculate_stars(percentage):
    """
    Star rating logic from the API contract:
      90–100% → 3 stars  (celebrating)
      70–89%  → 2 stars  (happy)
      Below 70% → 1 star (encouraging)
    """
    if percentage >= 90:
        return 3, "celebrating"
    elif percentage >= 70:
        return 2, "happy"
    else:
        return 1, "encouraging"


def hash_password(raw):
    """Hash passwords with Django's configured password hasher."""
    return make_password(raw)


def password_matches(raw, stored):
    """Support new Django hashes and legacy SHA-256 sample accounts."""
    if check_password(raw, stored):
        return True
    return stored == hashlib.sha256(raw.encode()).hexdigest()


def set_learner_session(request, child):
    request.session.flush()
    request.session['account_role'] = 'learner'
    request.session['account_id'] = child.id
    request.session['account_name'] = child.name
    request.session['child_id'] = child.id
    request.session['child_name'] = child.name
    request.session['child_grade'] = child.grade


def session_child_matches(request, child_id):
    try:
        return int(request.session.get('child_id', 0)) == int(child_id)
    except (TypeError, ValueError):
        return False


def parse_grades(grades_taught):
    grades = []
    for raw_grade in (grades_taught or '').replace(';', ',').split(','):
        raw_grade = raw_grade.strip()
        if raw_grade.isdigit():
            grades.append(int(raw_grade))
    return grades


def teacher_can_view_child(teacher, child):
    if teacher.school_name.strip().lower() != child.school_name.strip().lower():
        return False
    grades = parse_grades(teacher.grades_taught)
    return not grades or child.grade in grades


def user_can_view_child(request, child):
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')

    if role == 'learner':
        return session_child_matches(request, child.id)

    if role == 'parent' and account_id:
        parent = Parent.objects.filter(id=account_id).first()
        return bool(parent and (child.parent_id == parent.id or child.parent_email.lower() == parent.email.lower()))

    if role == 'teacher' and account_id:
        teacher = Teacher.objects.filter(id=account_id).first()
        return bool(teacher and teacher_can_view_child(teacher, child))

    return False


def session_score_key(lesson_id, suffix):
    return f'lesson_{lesson_id}_{suffix}'


def session_score(request, lesson_id, suffix, default=0):
    try:
        return int(request.session.get(session_score_key(lesson_id, suffix), default))
    except (TypeError, ValueError):
        return default


def normalise_spelling_answer(value, loose=False):
    value = ' '.join((value or '').strip().lower().split())
    if loose:
        for character in '.,!?;:\'"()[]{}-':
            value = value.replace(character, '')
        value = ' '.join(value.split())
    return value


def missing_letters_for(activity):
    display_text = activity.display_text or ''
    answer = activity.answer or ''
    return ''.join(
        answer[index]
        for index, character in enumerate(display_text)
        if character == '_' and index < len(answer)
    )


def spelling_answer_is_correct(activity, raw_answer):
    if activity.activity_type == SpellingActivity.FILL_VOWEL:
        missing_letters = missing_letters_for(activity)
        accepted_answers = [activity.answer]
        if missing_letters:
            accepted_answers.append(missing_letters)
        return any(
            normalise_spelling_answer(raw_answer) == normalise_spelling_answer(answer)
            for answer in accepted_answers
        )

    if activity.activity_type == SpellingActivity.COPY_WRITING:
        return normalise_spelling_answer(raw_answer, loose=True) == normalise_spelling_answer(
            activity.answer,
            loose=True,
        )

    return normalise_spelling_answer(raw_answer) == normalise_spelling_answer(activity.answer)


def looks_like_readable_english_text(value):
    """Reject gibberish but allow a capitalised proper name as a sensible answer."""
    text = str(value or '').strip()
    if not text:
        return False
    text = text.replace('’', "'")
    if re.search(r'[^A-Za-z\s\'\-.,!?;:]', text):
        return False

    words = re.findall(r"[A-Za-z']+", text)
    if not words:
        return False

    lower_words = [word.lower() for word in words]
    common_words = {
        'a', 'i', 'the', 'and', 'but', 'or', 'if', 'as', 'at', 'be', 'by', 'for', 'from', 'in', 'into', 'it',
        'its', 'of', 'on', 'or', 'that', 'this', 'to', 'too', 'up', 'with', 'was', 'were', 'is', 'are', 'am',
        'he', 'she', 'they', 'them', 'their', 'we', 'you', 'your', 'our', 'us', 'me', 'my', 'his', 'her',
        'because', 'before', 'after', 'while', 'when', 'then', 'there', 'here', 'again', 'one', 'two', 'three',
        'went', 'came', 'looked', 'found', 'helped', 'help', 'made', 'felt', 'thought', 'said', 'saw', 'told',
        'smiled', 'laughed', 'ran', 'walked', 'played', 'read', 'write', 'writing', 'asked', 'asked', 'called',
        'school', 'teacher', 'friend', 'friends', 'family', 'dog', 'cat', 'home', 'story', 'answer', 'questions',
        'happy', 'sad', 'angry', 'afraid', 'proud', 'worried', 'excited', 'nervous', 'quiet', 'little', 'big',
        'good', 'bad', 'right', 'wrong', 'strong', 'quick', 'slow', 'early', 'late', 'inside', 'outside', 'under',
        'next', 'last', 'first', 'day', 'days', 'night', 'morning', 'afternoon', 'evening', 'time', 'times',
        'people', 'child', 'children', 'man', 'woman', 'boy', 'girl', 'name', 'names', 'mum', 'dad', 'mother',
        'father', 'grandma', 'grandpa', 'class', 'room', 'house', 'teacher', 'book', 'books', 'page', 'pages',
        'rain', 'sun', 'wind', 'cloud', 'clouds', 'water', 'ground', 'road', 'tree', 'trees', 'park', 'field',
    }

    capitalised_name = bool(words) and all(re.fullmatch(r"[A-Z][a-zA-Z']+", word) for word in words)
    if capitalised_name and len(words) <= 3:
        return True

    if len(words) < 2:
        return False
    if any(len(word) < 2 and word.lower() not in {'a', 'i'} for word in words):
        return False
    if any(re.fullmatch(r"[bcdfghjklmnpqrstvwxyz]{4,}", word.lower()) for word in words):
        return False
    if any(word.lower() in {'qwerty', 'asdf', 'zxcvbn', 'lkjhg'} for word in words):
        return False

    return any(word.lower() in common_words for word in words) or sum(
        1 for word in lower_words if word in common_words
    ) >= max(1, len(words) // 2)


def has_two_punctuated_sentences(value):
    """Require at least two sentences that end with punctuation."""
    text = str(value or '').strip()
    return len(re.findall(r'[.!?](?=\s|$)', text)) >= 2


def normalise_reading_answer(value):
    """Compare short learner answers without case or punctuation noise."""
    value = str(value or '').strip().lower()
    for character in '.,!?;:\"\'()[]{}-':
        value = value.replace(character, '')
    return ' '.join(value.split())


def structured_reading_answer(activity):
    try:
        value = json.loads(activity.correct_answer or '{}')
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def reading_answer_score(activity, child_answer):
    if activity.activity_type == ReadingActivity.SEQUENCING:
        correct = list(child_answer or []) == list(activity.items_in_correct_order or [])
        return (1 if correct else 0), 1

    if activity.activity_type in {
        ReadingActivity.CROSSWORD,
        ReadingActivity.WORD_SCRAMBLE,
    }:
        expected = structured_reading_answer(activity)
        submitted = child_answer if isinstance(child_answer, dict) else {}
        assessed = {
            str(key): submitted.get(str(key), submitted.get(key, ''))
            for key in expected
            if str(submitted.get(str(key), submitted.get(key, '')) or '').strip()
        }
        score = 0
        for key, child_value in assessed.items():
            answer = expected[key]
            correct = normalise_reading_answer(child_value) == normalise_reading_answer(answer)
            score += int(correct)
        return score, len(assessed)

    if activity.activity_type == ReadingActivity.MATCHING:
        if isinstance(activity.options, dict):
            expected = structured_reading_answer(activity)
            submitted = child_answer if isinstance(child_answer, dict) else {}
            assessed = {
                str(key): submitted.get(str(key), submitted.get(key, ''))
                for key in expected
                if str(submitted.get(str(key), submitted.get(key, '')) or '').strip()
            }
            score = 0
            for key, child_value in assessed.items():
                answer = expected[key]
                correct = str(child_value) == str(answer)
                score += int(correct)
            return score, len(assessed)

        correct = normalise_reading_answer(child_answer) == normalise_reading_answer(activity.correct_answer)
        return (1 if correct else 0), 1

    correct = normalise_reading_answer(child_answer) == normalise_reading_answer(activity.correct_answer)
    return (1 if correct else 0), 1


def reading_answer_is_correct(activity, child_answer):
    score, total = reading_answer_score(activity, child_answer)
    return bool(total and score == total)


def reading_model_answer(activity):
    if activity.activity_type == ReadingActivity.SEQUENCING:
        return ' -> '.join(activity.items_in_correct_order or [])
    if activity.activity_type in {
        ReadingActivity.CROSSWORD,
        ReadingActivity.WORD_SCRAMBLE,
    }:
        return '; '.join(structured_reading_answer(activity).values())
    if activity.activity_type == ReadingActivity.MATCHING:
        if not isinstance(activity.options, dict):
            return str(activity.correct_answer or '')
        config = activity.options if isinstance(activity.options, dict) else {}
        prompts = {str(item.get('key')): item.get('text', '') for item in config.get('prompts', [])}
        choices = {str(item.get('key')): item.get('text', '') for item in config.get('choices', [])}
        return '; '.join(
            f"{prompts.get(str(prompt_key), prompt_key)}: {choices.get(str(choice_key), choice_key)}"
            for prompt_key, choice_key in structured_reading_answer(activity).items()
        )
    return activity.correct_answer

# ─────────────────────────────────────────────────────────────
# OTP HELPERS
# ─────────────────────────────────────────────────────────────

def generate_otp():
    """Generate a 6-digit numeric OTP."""
    return str(random.randint(100000, 999999))


def send_otp_email(email, code, full_name):
    """Send the OTP code to the user's email address."""
    subject = "Your SGILA verification code"
    message = (
        f"Hi {full_name},\n\n"
        f"Your SGILA verification code is: {code}\n\n"
        f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
        f"If you did not create a SGILA account, please ignore this email.\n\n"
        f"— The SGILA Team"
    )
    send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)


# ─────────────────────────────────────────────────────────────
# SCREEN 2 — REGISTRATION (Step 1: validate + send OTP)
# POST /api/register
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    """
    Screen 2 — Registration (Step 1 of 2)
    Validates form data, stores it as pending, generates a 6-digit OTP,
    sends it to the user's email, and returns a session key for the OTP page.

    Frontend sends: role, full_name, email, password
                    + school_name (teacher) | accepted_popia (parent/teacher)
    Backend returns: message, email_masked, otp_session
    """
    data = json_body(request)
    role = data.get('role', 'parent')

    if role not in ('parent', 'teacher'):
        return JsonResponse({'error': 'Invalid role.'}, status=400)

    email = (data.get('email') or '').strip().lower()
    full_name = title_case(data.get('full_name'))
    data['full_name'] = full_name
    if role == 'teacher':
        data['school_name'] = title_case(data.get('school_name'))
    password = data.get('password', '')

    if not email or not full_name or not password:
        return JsonResponse({'error': 'full_name, email, and password are required.'}, status=400)

    # accepted_popia must be explicitly true — don't let it default/fall through
    if not data.get('accepted_popia') in (True, 'true', 'True'):
        return JsonResponse({'error': 'You must accept the Terms & Conditions to register.'}, status=400)
 
    if role == 'parent' and Parent.objects.filter(email=email).exists():
        return JsonResponse({'error': 'That email is already registered.'}, status=400)
    if role == 'teacher' and Teacher.objects.filter(email=email).exists():
        return JsonResponse({'error': 'That email is already registered.'}, status=400)

    # Invalidate any previous unused OTPs for this email+role
    OTPToken.objects.filter(email=email, role=role, is_used=False).delete()

    code = generate_otp()

    otp = OTPToken.objects.create(
        email=email,
        role=role,
        code=code,
        pending_data=json.dumps(data),
    )

    send_otp_email(email, code, full_name)

    local, domain = email.split('@', 1)
    masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'

    return JsonResponse({
        'message': 'OTP sent. Please check your email.',
        'email_masked': masked,
        'otp_session': str(otp.id),
    }, status=200)


# ─────────────────────────────────────────────────────────────
# OTP VERIFICATION — completes registration
# POST /api/verify-otp
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """
    OTP Verification — Step 2 of registration.
    Frontend sends: otp_session (id), code (6 digits entered by user)
    Backend creates the account and returns a JWT access token.
    """
    data = json_body(request)
    session_id = data.get('otp_session')
    code = (data.get('code') or '').strip()

    if not session_id or not code:
        return JsonResponse({'error': 'otp_session and code are required.'}, status=400)

    try:
        otp = OTPToken.objects.get(id=session_id, is_used=False)
    except OTPToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired verification session.'}, status=400)

    if otp.is_expired():
        return JsonResponse({'error': 'OTP has expired. Please register again to get a new code.'}, status=400)

    if otp.code != code:
        return JsonResponse({'error': 'Incorrect code. Please try again.'}, status=400)

    otp.is_used = True
    otp.save()

    pending = json.loads(otp.pending_data)
    role = otp.role
    email = otp.email

    if role == 'parent':
        account = Parent.objects.create(
            full_name=pending.get('full_name', '').strip(),
            email=email,
            phone=pending.get('phone', '').strip(),
            password=make_password(pending.get('password', '')),
            accepted_popia=bool(pending.get('accepted_popia')),
        )
        # Same as the web registration flow — the free trial runs on the
        # Family plan, created eagerly so plan_type is never ambiguous.
        Subscription.objects.create(parent=account, plan_type='family', status='trial')
        redirect_to = '/parent/dashboard'
    else:
        account = Teacher.objects.create(
            full_name=pending.get('full_name', '').strip(),
            email=email,
            school_name=pending.get('school_name', '').strip(),
            grades_taught=pending.get('grades_taught', ''),
            phone=pending.get('phone', '').strip(),
            password=make_password(pending.get('password', '')),
            accepted_popia=bool(pending.get('accepted_popia')),
        )
        redirect_to = '/teacher/dashboard'

    token = create_access_token({
        'sub': account.id,
        'role': role,
        'email': email,
        'name': account.full_name,
        'grade': None,
    })

    return JsonResponse({
        'message': 'Email verified. Account created successfully.',
        'access_token': token,
        'role': role,
        'name': account.full_name,
        'account_id': account.id,
        'redirect_to': redirect_to,
    }, status=201)


# ─────────────────────────────────────────────────────────────
# OTP RESEND
# POST /api/resend-otp
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def resend_otp(request):
    """
    Resend a fresh OTP for an existing pending registration session.
    Frontend sends: otp_session (id)
    """
    data = json_body(request)
    session_id = data.get('otp_session')

    try:
        old_otp = OTPToken.objects.get(id=session_id, is_used=False)
    except OTPToken.DoesNotExist:
        return JsonResponse({'error': 'Session not found or already used.'}, status=400)

    pending = json.loads(old_otp.pending_data)
    full_name = pending.get('full_name', 'there')

    old_otp.is_used = True
    old_otp.save()

    new_code = generate_otp()
    new_otp = OTPToken.objects.create(
        email=old_otp.email,
        role=old_otp.role,
        code=new_code,
        pending_data=old_otp.pending_data,
    )

    send_otp_email(old_otp.email, new_code, full_name)

    return JsonResponse({
        'message': 'A new code has been sent to your email.',
        'otp_session': str(new_otp.id),
    })


# ─────────────────────────────────────────────────────────────
# SCREEN 3 — LOGIN
# POST /api/login
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    """
    Screen 3 — Login Screen
    Supports all three roles: learner, parent, teacher.
    Frontend sends: email (or username for learner), password, role
    Backend returns: login_successful, access_token (JWT), role, name, account_id, redirect_to
    On failure: login_successful=false + message
    """
    data = json_body(request)
    role = data.get('role', 'learner')

    if role not in ('learner', 'parent', 'teacher'):
        return JsonResponse({'login_successful': False, 'message': 'Invalid role.'}, status=400)

    password = data.get('password', '')

    if role == 'learner':
        login_value = data.get('email', '') or data.get('username', '')
        child = Child.objects.filter(
            Q(parent_email__iexact=login_value) | Q(username__iexact=login_value)
        ).first()
        if not child or not password_matches(password, child.password):
            return JsonResponse({'login_successful': False, 'message': 'Incorrect username or password.'}, status=401)
        allowed, reason = child_access_status(child)
        if not allowed:
            request.session.flush()
            return JsonResponse({
                'login_successful': False,
                'access_blocked': True,
                'reason': reason,
                'message': 'Learner access is paused. Ask a parent to check the SGILA account.',
                'redirect_to': f'/account-access?reason={reason}',
            }, status=403)
        set_learner_session(request, child)
        linked_parent = linked_parent_for_child(child)
        token = create_access_token({
            'sub': child.id,
            'role': 'learner',
            'email': child.parent_email,
            'name': child.name,
            'grade': child.grade,
            'parent_auth_version': linked_parent.auth_version if linked_parent else None,
        })
        return JsonResponse({
            'login_successful': True,
            'access_token': token,
            'role': 'learner',
            'name': child.name,
            'account_id': child.id,
            'child_id': child.id,
            'grade': child.grade,
            'redirect_to': f'/grade/{child.grade}',
        })
    else:
        email = (data.get('email') or '').strip().lower()
        model = {'parent': Parent, 'teacher': Teacher}[role]
        try:
            account = model.objects.get(email=email)
        except model.DoesNotExist:
            return JsonResponse({'login_successful': False, 'message': 'Incorrect email or password.'}, status=401)
        if not password_matches(password, account.password):
            return JsonResponse({'login_successful': False, 'message': 'Incorrect email or password.'}, status=401)
        if role in ('parent', 'teacher') and not account.is_active:
            request.session.flush()
            request.session['pending_reactivation_role'] = role
            request.session['pending_reactivation_account_id'] = account.id
            request.session['pending_reactivation_verified_at'] = int(timezone.now().timestamp())
            return JsonResponse({
                'login_successful': False,
                'reactivation_required': True,
                'message': 'This account is deactivated. Confirm reactivation to continue.',
                'redirect_to': '/account/reactivate',
            }, status=403)
        token = create_access_token({
            'sub': account.id,
            'role': role,
            'email': email,
            'name': account.full_name,
            'grade': None,
            'auth_version': getattr(account, 'auth_version', 0),
        })
        return JsonResponse({
            'login_successful': True,
            'access_token': token,
            'role': role,
            'name': account.full_name,
            'account_id': account.id,
            'redirect_to': f'/{role}/dashboard',
        })


# ─────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Step 1: Request reset link
# POST /api/forgot-password
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def forgot_password(request):
    """
    Forgot Password — Step 1.
    Frontend sends: email, role ('parent' or 'teacher')
    Backend: looks up the account, generates a secure token, sends a reset
             email with a link to /reset-password?token=<token>&role=<role>
    Always returns a generic success message (don't reveal if email exists).
    """
    data = json_body(request)
    email = (data.get('email') or '').strip().lower()
    role = data.get('role', '').strip()

    if role not in ('parent', 'teacher'):
        return JsonResponse({'error': 'Invalid role. Must be parent or teacher.'}, status=400)
    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)

    model = Parent if role == 'parent' else Teacher
    account = model.objects.filter(email=email).first()

    if account:
        # Invalidate any existing unused tokens for this email/role
        PasswordResetToken.objects.filter(email=email, role=role, is_used=False).update(is_used=True)

        token = secrets.token_urlsafe(48)
        PasswordResetToken.objects.create(email=email, role=role, token=token)

        reset_url = f"{django_settings.SITE_URL.rstrip('/')}/reset-password?token={token}&role={role}"
        subject = "Reset your SGILA password"
        message = (
            f"Hi {account.full_name},\n\n"
            f"We received a request to reset your SGILA password.\n\n"
            f"Click the link below to choose a new password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 30 minutes. If you did not request a password reset, "
            f"you can safely ignore this email — your password will not change.\n\n"
            f"— The SGILA Team"
        )
        try:
            send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        except Exception:
            pass  # Silently fail so we don't leak account existence

    # Always return the same response regardless of whether the account exists
    return JsonResponse({
        'message': 'If an account with that email exists, a reset link has been sent.'
    })


# ─────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Step 2: Submit new password
# POST /api/reset-password
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    """
    Forgot Password — Step 2.
    Frontend sends: token, role, new_password
    Backend: validates the token, updates the account password, marks token used.
    """
    data = json_body(request)
    token_value = (data.get('token') or '').strip()
    role = (data.get('role') or '').strip()
    new_password = data.get('new_password', '')

    if not token_value or not role or not new_password:
        return JsonResponse({'error': 'token, role, and new_password are required.'}, status=400)
    if role not in ('parent', 'teacher'):
        return JsonResponse({'error': 'Invalid role.'}, status=400)
    pw_errors = password_strength_errors(new_password)
    if pw_errors:
        return JsonResponse({'error': ' '.join(pw_errors)}, status=400)

    try:
        reset_token = PasswordResetToken.objects.get(token=token_value, role=role, is_used=False)
    except PasswordResetToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired reset link. Please request a new one.'}, status=400)

    if reset_token.is_expired():
        reset_token.is_used = True
        reset_token.save()
        return JsonResponse({'error': 'This reset link has expired. Please request a new one.'}, status=400)

    model = Parent if role == 'parent' else Teacher
    account = model.objects.filter(email=reset_token.email).first()
    if not account:
        return JsonResponse({'error': 'Account not found.'}, status=404)

    account.password = make_password(new_password)
    account.save()

    reset_token.is_used = True
    reset_token.save()

    return JsonResponse({'message': 'Your password has been reset. You can now sign in.'})


# ─────────────────────────────────────────────────────────────
# SCREEN 4 — GRADE HOME PAGE
# GET /api/lessons?grade=1
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def lesson_list(request):
    """
    Screen 4 — Grade Home Page
    Frontend sends: ?grade=1 (or 2) as a URL query parameter
    Backend returns: list of lesson cards for that grade

    Example: GET /api/lessons?grade=1
    Returns: [{"id":1, "title":"Lerato's Fruit Basket", "grade":1, ...}]
    """
    grade = request.GET.get('grade')
    if not grade:
        return JsonResponse({'error': 'Missing ?grade= parameter'}, status=400)

    lessons = Lesson.objects.filter(grade=grade)
    data = []
    for lesson in lessons:
        # Check if child has completed this lesson
        child_id = request.GET.get('child_id')
        completed = False
        if child_id:
            completed = Progress.objects.filter(
                child_id=child_id, lesson=lesson
            ).exists()

        data.append({
            'id': lesson.id,
            'title': lesson.title,
            'grade': lesson.grade,
            'thumbnail_image': lesson.thumbnail_image,
            'completed': completed,
        })

    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────
# SCREEN 5 — STORY SCREEN
# GET /api/lessons/1/story
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def story(request, lesson_id):
    """
    Screen 5 — Story Screen
    Frontend sends: lesson_id in the URL
    Backend returns: all pages of the story with text, image, audio, highlighted_words
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    pages = []
    for page in lesson.pages.all():
        pages.append({
            'page_number': page.page_number,
            'text': page.text,
            'image_url': page.image_url,
            'audio_url': page.audio_url,
            'highlighted_words': page.get_highlighted_words(),
        })

    return JsonResponse({
        'lesson_id': lesson.id,
        'title': lesson.title,
        'pages': pages,
    })


# ─────────────────────────────────────────────────────────────
# SCREEN 6 — COMPREHENSION QUESTIONS
# GET  /api/lessons/1/questions
# POST /api/check-answer
# ─────────────────────────────────────────────────────────────

@never_cache
@require_http_methods(["GET"])
def questions(request, lesson_id):
    """
    Screen 6 Step A — Fetch all questions for a lesson.
    NOTE: correct_answer is NOT included — it is kept secret until the child answers.
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    data = []
    activities = list(lesson.reading_activities.all())
    if activities:
        for activity in activities:
            item = {
                'activity_id': activity.id,
                'activity_type': activity.activity_type,
                'skill': activity.skill,
                'question': activity.question,
                'options': activity.get_options(),
                'requires_review': activity.requires_review,
                'group_number': activity.group_number or activity.order,
                'group_title': activity.group_title or activity.get_activity_type_display(),
            }
            if activity.activity_type == ReadingActivity.SEQUENCING:
                shuffled_items = list(activity.items_in_correct_order or [])
                random.shuffle(shuffled_items)
                if len(shuffled_items) > 1 and shuffled_items == activity.items_in_correct_order:
                    shuffled_items = shuffled_items[1:] + shuffled_items[:1]
                item['items'] = shuffled_items
            data.append(item)
    else:
        for q in lesson.questions.all():
            data.append({
                'question_id': q.id,
                'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                'skill': 'literal_comprehension',
                'question': q.question,
                'options': q.get_options(),
                'requires_review': False,
                # correct_answer intentionally excluded here
            })

    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def check_reading_activity(request):
    """Check a varied comprehension activity without exposing answers first."""
    data = json_body(request)
    lesson_id = data.get('lesson_id')
    child_id = data.get('child_id')

    if not session_child_matches(request, child_id):
        return JsonResponse({'error': 'You do not have access to this learner attempt.'}, status=403)

    try:
        lesson_id = int(lesson_id)
        activity = ReadingActivity.objects.get(id=data.get('activity_id'), lesson_id=lesson_id)
        child = Child.objects.get(id=child_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid lesson or activity id.'}, status=400)
    except ReadingActivity.DoesNotExist:
        return JsonResponse({'error': 'Activity not found.'}, status=404)
    except Child.DoesNotExist:
        return JsonResponse({'error': 'Child not found.'}, status=404)

    child_answer = data.get('child_answer')
    is_guided_writing = (
        activity.requires_review
        and isinstance(activity.options, dict)
        and activity.options.get('writing_template') is True
    )
    if activity.activity_type == ReadingActivity.SEQUENCING:
        has_answer = isinstance(child_answer, list) and any(str(item).strip() for item in child_answer)
    elif activity.activity_type in {
        ReadingActivity.CROSSWORD,
        ReadingActivity.WORD_SCRAMBLE,
    }:
        has_answer = isinstance(child_answer, dict) and any(
            str(value or '').strip() for value in child_answer.values()
        )
    elif activity.activity_type == ReadingActivity.MATCHING:
        has_answer = (
            (isinstance(child_answer, dict) and any(str(value or '').strip() for value in child_answer.values()))
            or (isinstance(child_answer, str) and bool(str(child_answer).strip()))
            or (isinstance(child_answer, list) and any(str(item).strip() for item in child_answer))
        )
    else:
        has_answer = bool(str(child_answer or '').strip())
    if not has_answer:
        return JsonResponse({'error': 'Please answer before continuing.'}, status=400)

    if is_guided_writing:
        if not isinstance(child_answer, dict):
            return JsonResponse({'error': 'Please complete the diary entry before saving.'}, status=400)
        required_fields = {'feeling', 'because', 'best_part', 'next_time', 'from_name'}
        if any(not str(child_answer.get(field, '')).strip() for field in required_fields):
            return JsonResponse({'error': 'Please complete every diary line before saving.'}, status=400)
        ReadingActivityResponse.objects.update_or_create(
            child=child,
            lesson=activity.lesson,
            defaults={
                'activity': activity,
                'response': child_answer,
            },
        )

    if activity.requires_review and isinstance(child_answer, str):
        if activity.activity_type == ReadingActivity.OPEN_ENDED and not has_two_punctuated_sentences(child_answer):
            return JsonResponse({'error': 'Please write two or more sentences and use your punctuation.'}, status=400)
        if not looks_like_readable_english_text(child_answer):
            return JsonResponse({'error': 'That answer is not clear enough. Please try again.'}, status=400)

    review_required = activity.requires_review
    awarded, possible = reading_answer_score(activity, child_answer)
    if review_required:
        awarded, possible = 1, 1
        is_correct = None
    else:
        is_correct = bool(possible and awarded == possible)

    answers_key = session_score_key(lesson_id, 'reading_activity_answers')
    answers = request.session.get(answers_key, {})
    activity_key = f'activity-{activity.id}'
    answers[activity_key] = {
        'score': awarded,
        'total': possible,
        'skill': activity.skill,
    }
    request.session[answers_key] = answers

    skill_scores = {}
    for result in answers.values():
        if isinstance(result, dict):
            bucket = skill_scores.setdefault(result.get('skill') or 'reading', {'score': 0, 'total': 0})
            bucket['score'] += int(result.get('score') or 0)
            bucket['total'] += int(result.get('total') or 0)
        else:
            bucket = skill_scores.setdefault('reading', {'score': 0, 'total': 0})
            bucket['score'] += int(result or 0)
            bucket['total'] += 1

    request.session[session_score_key(lesson_id, 'reading_skill_scores')] = skill_scores
    request.session[session_score_key(lesson_id, 'comprehension_score')] = sum(
        result['score'] for result in skill_scores.values()
    )
    request.session[session_score_key(lesson_id, 'comprehension_total')] = sum(
        result['total'] for result in skill_scores.values()
    )
    request.session.modified = True

    if is_guided_writing:
        message = f'Your diary entry is saved to your profile, {child.name}.'
    elif review_required:
        message = f'Thank you, {child.name}. Compare your idea with the example.'
    elif is_correct:
        message = f'Well done, {child.name}! That answer shows careful reading.'
    elif awarded:
        message = f'You got {awarded} out of {possible}. Check the remaining story clues.'
    else:
        message = 'Not quite. Read the story clue and compare it with the answer.'

    model_answer = reading_model_answer(activity)
    if activity.activity_type in {ReadingActivity.CROSSWORD, ReadingActivity.WORD_SCRAMBLE}:
        correct_answer = structured_reading_answer(activity)
    elif activity.activity_type == ReadingActivity.MATCHING and isinstance(activity.options, dict):
        correct_answer = structured_reading_answer(activity)
    else:
        correct_answer = activity.correct_answer

    return JsonResponse({
        'correct': is_correct,
        'partial': bool(awarded and awarded < possible),
        'score_awarded': awarded,
        'score_possible': possible,
        'review_required': review_required,
        'saved': is_guided_writing,
        'correct_answer': correct_answer,
        'model_answer': model_answer,
        'message': message,
        'comprehension_score': request.session.get(session_score_key(lesson_id, 'comprehension_score'), 0),
        'comprehension_total': request.session.get(session_score_key(lesson_id, 'comprehension_total'), 0),
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_answer(request):
    """
    Screen 6 Step B — Check if the child's answer is correct.
    Frontend sends: child_id, lesson_id, question_id, child_answer
    Backend returns: correct (true/false), correct_answer, mascot_reaction, message
    """
    data = json_body(request)
    lesson_id = data.get('lesson_id')
    child_id = data.get('child_id')

    if not session_child_matches(request, child_id):
        return JsonResponse({'error': 'You do not have access to this learner attempt.'}, status=403)

    try:
        question = ComprehensionQuestion.objects.get(id=data.get('question_id'))
    except ComprehensionQuestion.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)

    try:
        child = Child.objects.get(id=child_id)
    except Child.DoesNotExist:
        return JsonResponse({'error': 'Child not found'}, status=404)

    try:
        lesson_id = int(lesson_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid lesson id.'}, status=400)

    if question.lesson_id != lesson_id:
        return JsonResponse({'error': 'Question does not belong to this lesson.'}, status=400)

    is_correct = data.get('child_answer') == question.correct_answer
    answers_key = session_score_key(question.lesson_id, 'question_answers')
    answers = request.session.get(answers_key, {})
    question_key = str(question.id)
    if question_key not in answers:
        answers[question_key] = bool(is_correct)
        request.session[answers_key] = answers
        request.session[session_score_key(question.lesson_id, 'comprehension_score')] = sum(1 for value in answers.values() if value)
        request.session[session_score_key(question.lesson_id, 'comprehension_total')] = question.lesson.questions.count()
        request.session.modified = True

    if is_correct:
        return JsonResponse({
            'correct': True,
            'correct_answer': question.correct_answer,
            'mascot_reaction': 'celebrating',
            'message': f'Well done {child.name}! {question.correct_answer} is correct!',
            'comprehension_score': request.session.get(session_score_key(question.lesson_id, 'comprehension_score'), 0),
            'comprehension_total': request.session.get(session_score_key(question.lesson_id, 'comprehension_total'), 0),
        })
    else:
        return JsonResponse({
            'correct': False,
            'correct_answer': question.correct_answer,
            'mascot_reaction': 'encouraging',
            'message': f'Not quite! The correct answer is {question.correct_answer}. You can do it!',
            'comprehension_score': request.session.get(session_score_key(question.lesson_id, 'comprehension_score'), 0),
            'comprehension_total': request.session.get(session_score_key(question.lesson_id, 'comprehension_total'), 0),
        })


# ─────────────────────────────────────────────────────────────
# SCREEN 7 — VISUAL ACTIVITY
# GET /api/lessons/1/visual-activity
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def visual_activity(request, lesson_id):
    """
    Screen 7 — Visual Activity (match image to word)
    Returns all image-word pairs with shuffled word options.
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    items = []
    for item in lesson.visual_items.all():
        items.append({
            'item_id': item.id,
            'image_url': item.image_url,
            'word_options': item.get_word_options(),
        })

    return JsonResponse({
        'activity_type': 'match-image-to-word',
        'items': items,
    })


# ─────────────────────────────────────────────────────────────
# SCREEN 8 — AUDIO PRONUNCIATION
# GET /api/lessons/1/pronunciation
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def check_visual_answer(request):
    """
    Check one visual matching answer and store the score in the server session.
    """
    data = json_body(request)
    child_id = data.get('child_id')
    lesson_id = data.get('lesson_id')

    if not session_child_matches(request, child_id):
        return JsonResponse({'error': 'You do not have access to this learner attempt.'}, status=403)

    try:
        lesson_id = int(lesson_id)
        item = VisualActivityItem.objects.get(id=data.get('item_id'), lesson_id=lesson_id)
    except (TypeError, ValueError, VisualActivityItem.DoesNotExist):
        return JsonResponse({'error': 'Visual activity item not found.'}, status=404)

    selected_word = (data.get('selected_word') or '').strip()
    is_correct = selected_word == item.correct_word
    answers_key = session_score_key(lesson_id, 'visual_answers')
    answers = request.session.get(answers_key, {})
    item_key = str(item.id)
    if item_key not in answers:
        answers[item_key] = bool(is_correct)
        request.session[answers_key] = answers
        request.session[session_score_key(lesson_id, 'visual_score')] = sum(1 for value in answers.values() if value)
        request.session[session_score_key(lesson_id, 'visual_total')] = VisualActivityItem.objects.filter(lesson_id=lesson_id).count()
        request.session.modified = True

    visual_total = request.session.get(session_score_key(lesson_id, 'visual_total'), 0)
    visual_score = request.session.get(session_score_key(lesson_id, 'visual_score'), 0)
    answered_count = len(answers)

    return JsonResponse({
        'correct': is_correct,
        'correct_word': item.correct_word,
        'visual_score': visual_score,
        'visual_total': visual_total,
        'answered_count': answered_count,
        'completed': answered_count >= visual_total,
    })


@require_http_methods(["GET"])
def pronunciation(request, lesson_id):
    """
    Screen 8 — Audio Pronunciation (English + isiZulu)
    Returns all words with their audio files in both languages.
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    data = []
    for word in lesson.pronunciation_words.all():
        data.append({
            'word': word.word,
            'image_url': word.image_url,
            'english_audio': word.english_audio,
            'isizulu_audio': word.isizulu_audio,
            'isizulu_word': word.isizulu_word,
        })

    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────
# SCREEN 9 — SPELLING ACTIVITIES
# GET /api/lessons/1/spelling
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def spelling(request, lesson_id):
    """
    Screen 9 — Writing and Spelling (3 activities)
    Returns all three spelling activities for the lesson.
    Activity 1: fill-missing-vowel
    Activity 2: drag-letters
    Activity 3: copy-writing
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    result = {}
    activities = lesson.spelling_activities.all()

    fill_vowel_words = []
    drag_words = []
    copy_sentences = []

    for act in activities:
        if act.activity_type == SpellingActivity.FILL_VOWEL:
            fill_vowel_words.append({
                'display': act.display_text,
            })
        elif act.activity_type == SpellingActivity.DRAG_LETTERS:
            drag_words.append({
                'scrambled': list(act.display_text.split(',')),
            })
        elif act.activity_type == SpellingActivity.COPY_WRITING:
            copy_sentences.append(act.answer)

    result['activity_1'] = {
        'type': 'fill-missing-vowel',
        'instruction': 'Fill in the missing letter to complete the word',
        'words': fill_vowel_words,
    }
    result['activity_2'] = {
        'type': 'drag-letters',
        'instruction': 'Drag the letters into the correct order',
        'words': drag_words,
    }
    result['activity_3'] = {
        'type': 'copy-writing',
        'instruction': 'Type this sentence exactly as you see it',
        'sentences': copy_sentences,
    }

    return JsonResponse(result)


# ─────────────────────────────────────────────────────────────
# SCREEN 10 — SAVE PROGRESS / RESULTS
# POST /api/progress
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def check_spelling_answer(request):
    """
    Check one spelling answer without exposing the stored answer in the HTML.
    """
    data = json_body(request)
    child_id = data.get('child_id')
    lesson_id = data.get('lesson_id')

    if not session_child_matches(request, child_id):
        return JsonResponse({'error': 'You do not have access to this learner attempt.'}, status=403)

    try:
        lesson_id = int(lesson_id)
        activity = SpellingActivity.objects.get(id=data.get('activity_id'), lesson_id=lesson_id)
    except (TypeError, ValueError, SpellingActivity.DoesNotExist):
        return JsonResponse({'error': 'Spelling activity not found.'}, status=404)

    answer = data.get('answer', '')
    if not normalise_spelling_answer(answer):
        return JsonResponse({
            'correct': False,
            'message': 'Type your answer first.',
        }, status=400)

    correct = spelling_answer_is_correct(activity, answer)
    # Store the running spelling score as each answer is checked. This lets the
    # learner's pause screen show an accurate score before the final form submit.
    answers_key = session_score_key(lesson_id, 'spelling_answers')
    answers = request.session.get(answers_key, {})
    answers[str(activity.id)] = bool(correct)
    request.session[answers_key] = answers
    request.session[session_score_key(lesson_id, 'spelling_score')] = sum(
        1 for is_correct in answers.values() if is_correct
    )
    request.session[session_score_key(lesson_id, 'spelling_total')] = SpellingActivity.objects.filter(
        lesson_id=lesson_id
    ).count()
    request.session.modified = True
    return JsonResponse({
        'correct': correct,
        'message': 'Correct! Great spelling.' if correct else 'Not quite. Check the missing letters and try again.',
    })


@csrf_exempt
@require_http_methods(["POST"])
def save_progress(request):
    """
    Screen 10 — End of Lesson Results
    Frontend sends all scores. Backend calculates stars and saves to database.
    Returns: stars_earned, percentage, mascot_reaction, message
    """
    data = json_body(request)
    child_id = data.get('child_id')
    lesson_id = data.get('lesson_id')

    if not session_child_matches(request, child_id):
        return JsonResponse({'error': 'You do not have access to this learner attempt.'}, status=403)

    try:
        lesson_id = int(lesson_id)
        child = Child.objects.get(id=child_id)
        lesson = Lesson.objects.get(id=lesson_id)
    except (Child.DoesNotExist, Lesson.DoesNotExist):
        return JsonResponse({'error': 'Child or lesson not found'}, status=404)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid child or lesson id.'}, status=400)

    score_keys = [
        'comprehension_score', 'comprehension_total', 'visual_score',
        'visual_total', 'spelling_score', 'spelling_total',
    ]
    if not any(session_score_key(lesson_id, key) in request.session for key in score_keys):
        return JsonResponse({'error': 'No completed lesson attempt found for this session.'}, status=400)

    comprehension_score = session_score(request, lesson_id, 'comprehension_score')
    visual_score = session_score(request, lesson_id, 'visual_score')
    spelling_score = session_score(request, lesson_id, 'spelling_score')
    comprehension_total = session_score(request, lesson_id, 'comprehension_total', lesson.questions.count())
    visual_total = session_score(request, lesson_id, 'visual_total', lesson.visual_items.count())
    spelling_total = session_score(request, lesson_id, 'spelling_total', lesson.spelling_activities.count())
    total_score = comprehension_score + visual_score + spelling_score
    total_possible = comprehension_total + visual_total + spelling_total
    percentage = round((total_score / total_possible) * 100) if total_possible else 0

    assessment_scores = {}
    reading_skill_scores = request.session.get(session_score_key(lesson_id, 'reading_skill_scores'), {})
    if isinstance(reading_skill_scores, dict) and reading_skill_scores:
        for key, values in reading_skill_scores.items():
            if isinstance(values, dict) and int(values.get('total') or 0):
                assessment_scores[key] = {
                    'score': int(values.get('score') or 0),
                    'total': int(values.get('total') or 0),
                }
    elif comprehension_total:
        assessment_scores['reading'] = {'score': comprehension_score, 'total': comprehension_total}
    if visual_total:
        assessment_scores['visual_literacy'] = {'score': visual_score, 'total': visual_total}
    if spelling_total:
        assessment_scores['spelling'] = {'score': spelling_score, 'total': spelling_total}

    stars, mascot_reaction = calculate_stars(percentage)

    Progress.objects.update_or_create(
        child=child,
        lesson=lesson,
        defaults={
            'comprehension_score': comprehension_score,
            'visual_score': visual_score,
            'spelling_score': spelling_score,
            'total_score': total_score,
            'total_possible': total_possible,
            'stars_earned': stars,
            'assessment_scores': assessment_scores,
        },
    )

    # Build the result message
    if stars == 3:
        message = f"Amazing work {child.name}! You are a star reader! You got {total_score} out of {total_possible}!"
    elif stars == 2:
        message = f"Great job {child.name}! You got {total_score} out of {total_possible}. Keep it up!"
    else:
        message = f"Good effort {child.name}! You got {total_score} out of {total_possible}. Keep practising!"

    return JsonResponse({
        'stars_earned': stars,
        'percentage': percentage,
        'mascot_reaction': mascot_reaction,
        'message': message,
    }, status=201)


# ─────────────────────────────────────────────────────────────
# SCREEN 11 — TEACHER / PARENT DASHBOARD
# GET /api/progress/1
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def get_progress(request, child_id):
    """
    Screen 11 — Teacher / Parent Dashboard
    Returns full lesson history for a child — every completed lesson with scores and stars.
    """
    try:
        child = Child.objects.get(id=child_id)
    except Child.DoesNotExist:
        return JsonResponse({'error': 'Child not found'}, status=404)

    if not user_can_view_child(request, child):
        return JsonResponse({'error': 'You do not have access to this learner progress.'}, status=403)

    records = Progress.objects.filter(child=child).select_related('lesson')
    data = []
    for record in records:
        data.append({
            'lesson': record.lesson.title,
            'grade': record.lesson.grade,
            'comprehension_score': record.comprehension_score,
            'visual_score': record.visual_score,
            'spelling_score': record.spelling_score,
            'total_score': record.total_score,
            'total_possible': record.total_possible,
            'stars_earned': record.stars_earned,
            'percentage': record.percentage,
            'assessment_scores': rows_for_record(record),
            'completed_on': record.completed_on.strftime('%Y-%m-%d'),
        })

    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────
# GRADE 4 ACTIVITY ENDPOINTS
# ─────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def vocabulary_activity(request, lesson_id):
    """Return vocabulary words with multiple-choice meanings."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    data = []
    for v in lesson.vocabulary_questions.all():
        data.append({
            'id': v.id,
            'word': v.word,
            'options': v.get_options(),
        })
    return JsonResponse({'activity_type': 'vocabulary-match', 'items': data})


@csrf_exempt
@require_http_methods(["POST"])
def check_vocabulary_answer(request):
    """Check one vocabulary answer and track score in session."""
    data = json_body(request)
    try:
        item = VocabularyQuestion.objects.get(id=data.get('item_id'))
    except VocabularyQuestion.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    is_correct = data.get('selected_option') == item.correct_answer
    lesson_id = item.lesson_id
    answers_key = f'lesson_{lesson_id}_vocab_answers'
    answers = request.session.get(answers_key, {})
    item_key = str(item.id)
    if item_key not in answers:
        answers[item_key] = bool(is_correct)
        request.session[answers_key] = answers
        request.session[f'lesson_{lesson_id}_vocab_score'] = sum(1 for v in answers.values() if v)
        request.session[f'lesson_{lesson_id}_vocab_total'] = VocabularyQuestion.objects.filter(lesson_id=lesson_id).count()
        request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': item.correct_answer,
        'message': 'Correct! Well done!' if is_correct else f'The correct answer is: {item.correct_answer}',
    })


@require_http_methods(["GET"])
def sequencing_activity(request, lesson_id):
    """Return the sequencing activity events in shuffled order."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    activity = lesson.sequencing_activities.first()
    if not activity:
        return JsonResponse({'error': 'No sequencing activity found'}, status=404)
    events_in_order = activity.get_events_in_order()
    shuffled = events_in_order[:]
    import random as _random
    _random.shuffle(shuffled)
    return JsonResponse({
        'activity_type': 'sequencing',
        'id': activity.id,
        'instruction': activity.instruction,
        'events': shuffled,
        'total': len(events_in_order),
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_sequencing_answer(request):
    """Check sequencing order and save score to session."""
    data = json_body(request)
    try:
        activity = SequencingActivity.objects.get(id=data.get('activity_id'))
    except SequencingActivity.DoesNotExist:
        return JsonResponse({'error': 'Activity not found'}, status=404)
    submitted = data.get('submitted_order', [])
    correct_order = activity.get_events_in_order()
    is_correct = submitted == correct_order
    lesson_id = activity.lesson_id
    request.session[f'lesson_{lesson_id}_seq_score'] = 1 if is_correct else 0
    request.session[f'lesson_{lesson_id}_seq_total'] = 1
    request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_order': correct_order,
        'message': 'Perfect order! Well done!' if is_correct else 'Not quite — check the correct order below.',
    })


@require_http_methods(["GET"])
def inference_activity(request, lesson_id):
    """Return inference questions for the lesson."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    data = []
    for q in lesson.inference_questions.all():
        data.append({
            'id': q.id,
            'question': q.question,
            'options': q.get_options(),
        })
    return JsonResponse({'activity_type': 'inference', 'questions': data})


@csrf_exempt
@require_http_methods(["POST"])
def check_inference_answer(request):
    """Check one inference answer and track score in session."""
    data = json_body(request)
    try:
        q = InferenceQuestion.objects.get(id=data.get('question_id'))
    except InferenceQuestion.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    is_correct = data.get('selected_option') == q.correct_answer
    lesson_id = q.lesson_id
    answers_key = f'lesson_{lesson_id}_inference_answers'
    answers = request.session.get(answers_key, {})
    qkey = str(q.id)
    if qkey not in answers:
        answers[qkey] = bool(is_correct)
        request.session[answers_key] = answers
        request.session[f'lesson_{lesson_id}_inference_score'] = sum(1 for v in answers.values() if v)
        request.session[f'lesson_{lesson_id}_inference_total'] = InferenceQuestion.objects.filter(lesson_id=lesson_id).count()
        request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': q.correct_answer,
        'message': 'Correct! Great thinking!' if is_correct else f'The correct answer is: {q.correct_answer}',
    })


@require_http_methods(["GET"])
def prediction_activity(request, lesson_id):
    """Return the prediction question with stop point."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    q = lesson.prediction_questions.first()
    if not q:
        return JsonResponse({'error': 'No prediction question found'}, status=404)
    return JsonResponse({
        'activity_type': 'prediction',
        'id': q.id,
        'stop_point_text': q.stop_point_text,
        'question': q.question,
        'options': q.get_options(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_prediction_answer(request):
    """Check the prediction answer and save to session."""
    data = json_body(request)
    try:
        q = PredictionQuestion.objects.get(id=data.get('question_id'))
    except PredictionQuestion.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    is_correct = data.get('selected_option') == q.correct_answer
    lesson_id = q.lesson_id
    request.session[f'lesson_{lesson_id}_prediction_score'] = 1 if is_correct else 0
    request.session[f'lesson_{lesson_id}_prediction_total'] = 1
    request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': q.correct_answer,
        'message': 'Correct! Good prediction!' if is_correct else f'The correct answer is: {q.correct_answer}',
    })


@require_http_methods(["GET"])
def feelings_activity(request, lesson_id):
    """Return feelings/emotional literacy questions."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    data = []
    for q in lesson.feelings_questions.all():
        data.append({
            'id': q.id,
            'question': q.question,
            'options': q.get_options(),
        })
    return JsonResponse({'activity_type': 'feelings', 'questions': data})


@csrf_exempt
@require_http_methods(["POST"])
def check_feelings_answer(request):
    """Check one feelings answer and track score in session."""
    data = json_body(request)
    try:
        q = FeelingsQuestion.objects.get(id=data.get('question_id'))
    except FeelingsQuestion.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    is_correct = data.get('selected_option') == q.correct_answer
    lesson_id = q.lesson_id
    answers_key = f'lesson_{lesson_id}_feelings_answers'
    answers = request.session.get(answers_key, {})
    qkey = str(q.id)
    if qkey not in answers:
        answers[qkey] = bool(is_correct)
        request.session[answers_key] = answers
        request.session[f'lesson_{lesson_id}_feelings_score'] = sum(1 for v in answers.values() if v)
        request.session[f'lesson_{lesson_id}_feelings_total'] = FeelingsQuestion.objects.filter(lesson_id=lesson_id).count()
        request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': q.correct_answer,
        'message': 'Correct! You understand feelings well!' if is_correct else f'The correct answer is: {q.correct_answer}',
    })


@require_http_methods(["GET"])
def cause_effect_activity(request, lesson_id):
    """Return cause-and-effect pairs for matching."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    pairs = list(lesson.cause_effect_pairs.all())
    import random as _random
    causes = [{'id': p.id, 'text': p.cause} for p in pairs]
    effects = [{'id': p.id, 'text': p.effect} for p in pairs]
    _random.shuffle(effects)
    return JsonResponse({
        'activity_type': 'cause-effect',
        'causes': causes,
        'effects': effects,
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_cause_effect_answer(request):
    """Check cause-effect matches and save total score to session when all are submitted."""
    data = json_body(request)
    cause_id = data.get('cause_id')
    effect_id = data.get('effect_id')
    is_correct = str(cause_id) == str(effect_id)
    correct_effect = None
    try:
        pair = CauseEffectPair.objects.get(id=cause_id)
        correct_effect = pair.effect
        lesson_id = pair.lesson_id
    except CauseEffectPair.DoesNotExist:
        return JsonResponse({'error': 'Pair not found'}, status=404)
    answers_key = f'lesson_{lesson_id}_ce_answers'
    answers = request.session.get(answers_key, {})
    ckey = str(cause_id)
    if ckey not in answers:
        answers[ckey] = bool(is_correct)
        request.session[answers_key] = answers
        total_pairs = CauseEffectPair.objects.filter(lesson_id=lesson_id).count()
        request.session[f'lesson_{lesson_id}_ce_score'] = sum(1 for v in answers.values() if v)
        request.session[f'lesson_{lesson_id}_ce_total'] = total_pairs
        request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_effect': correct_effect,
        'message': 'Correct match!' if is_correct else f'Not quite. The effect is: {correct_effect}',
    })


@require_http_methods(["GET"])
def theme_activity(request, lesson_id):
    """Return the theme/main lesson question."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    q = lesson.theme_questions.first()
    if not q:
        return JsonResponse({'error': 'No theme question found'}, status=404)
    return JsonResponse({
        'activity_type': 'theme',
        'id': q.id,
        'question': q.question,
        'options': q.get_options(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_theme_answer(request):
    """Check the theme answer and save to session."""
    data = json_body(request)
    try:
        q = ThemeQuestion.objects.get(id=data.get('question_id'))
    except ThemeQuestion.DoesNotExist:
        return JsonResponse({'error': 'Question not found'}, status=404)
    is_correct = data.get('selected_option') == q.correct_answer
    lesson_id = q.lesson_id
    request.session[f'lesson_{lesson_id}_theme_score'] = 1 if is_correct else 0
    request.session[f'lesson_{lesson_id}_theme_total'] = 1
    request.session.modified = True
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': q.correct_answer,
        'message': 'Correct! You found the main lesson!' if is_correct else f'The correct answer is: {q.correct_answer}',
    })


@require_http_methods(["GET"])
def written_response_activity(request, lesson_id):
    """Return the written response prompt."""
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)
    prompt = lesson.written_prompts.first()
    if not prompt:
        return JsonResponse({'error': 'No written prompt found'}, status=404)
    return JsonResponse({
        'activity_type': 'written-response',
        'id': prompt.id,
        'prompt': prompt.prompt,
        'guidance': prompt.guidance,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGING — Parent ↔ Teacher chat about a specific learner
# ══════════════════════════════════════════════════════════════════════════════

def _messaging_auth(request):
    """Session-based auth for messaging endpoints. Returns (payload, error) tuple."""
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')
    if not role or not account_id or role not in ('parent', 'teacher'):
        return None, JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
    return {'role': role, 'sub': int(account_id)}, None


def _get_child_or_403(child_id, payload):
    """Returns (child, error). Ensures caller is linked to this child."""
    try:
        child = Child.objects.select_related('parent', 'teacher').get(pk=child_id)
    except Child.DoesNotExist:
        return None, JsonResponse({'error': 'Learner not found.'}, status=404)

    role = payload['role']
    uid = payload['sub']

    if role == 'parent':
        parent_ok = (child.parent_id == uid)
        if not parent_ok:
            try:
                p = Parent.objects.get(pk=uid)
                parent_ok = bool(child.parent_email and child.parent_email.lower() == p.email.lower())
            except Parent.DoesNotExist:
                pass
        if not parent_ok:
            return None, JsonResponse({'error': 'You are not the parent of this learner.'}, status=403)

    if role == 'teacher' and child.teacher_id != uid:
        return None, JsonResponse({'error': 'This learner is not in your class.'}, status=403)

    return child, None


@csrf_exempt
@require_http_methods(['GET'])
def get_messages(request, child_id):
    """
    GET /api/messages/<child_id>
    Returns full conversation + child progress summary.
    Marks incoming messages as read automatically.
    """
    payload, err = _messaging_auth(request)
    if err:
        return err

    child, err = _get_child_or_403(child_id, payload)
    if err:
        return err

    opposite_role = 'teacher' if payload['role'] == 'parent' else 'parent'
    Message.objects.filter(child=child, sender_role=opposite_role, is_read=False).update(is_read=True)

    msgs_qs = Message.objects.filter(child=child).select_related('sender_parent', 'sender_teacher')
    messages_data = []
    for m in msgs_qs:
        sender_name = (m.sender_parent.full_name if m.sender_parent else 'Parent') \
            if m.sender_role == 'parent' else \
            (m.sender_teacher.full_name if m.sender_teacher else 'Teacher')
        messages_data.append({
            'id': m.id,
            'sender_role': m.sender_role,
            'sender_name': sender_name,
            'body': m.body,
            'sent_at': m.sent_at.isoformat(),
            'is_read': m.is_read,
        })

    progress_qs = Progress.objects.filter(child=child)
    stars_total = sum(p.stars_earned for p in progress_qs)
    lessons_completed = progress_qs.count()

    return JsonResponse({
        'child': {
            'id': child.id,
            'name': child.name,
            'grade': child.grade,
            'stars_total': stars_total,
            'lessons_completed': lessons_completed,
        },
        'messages': messages_data,
        'unread_count': Message.objects.filter(
            child=child, sender_role=opposite_role, is_read=False
        ).count(),
    })


@csrf_exempt
@require_http_methods(['POST'])
def send_message(request, child_id):
    """
    POST /api/messages/<child_id>/send
    Body: { "body": "..." }
    """
    payload, err = _messaging_auth(request)
    if err:
        return err

    child, err = _get_child_or_403(child_id, payload)
    if err:
        return err

    data = json_body(request)
    body = (data.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'Message body is required.'}, status=400)
    if len(body) > 2000:
        return JsonResponse({'error': 'Message is too long (max 2000 characters).'}, status=400)

    uid = payload['sub']
    role = payload['role']

    if role == 'parent':
        msg = Message.objects.create(child=child, sender_role='parent', sender_parent_id=uid, body=body)
        sender_name = msg.sender_parent.full_name if msg.sender_parent else 'Parent'
    else:
        msg = Message.objects.create(child=child, sender_role='teacher', sender_teacher_id=uid, body=body)
        sender_name = msg.sender_teacher.full_name if msg.sender_teacher else 'Teacher'

    return JsonResponse({
        'id': msg.id,
        'sender_role': msg.sender_role,
        'sender_name': sender_name,
        'body': msg.body,
        'sent_at': msg.sent_at.isoformat(),
    }, status=201)


@csrf_exempt
@require_http_methods(['GET'])
def unread_messages_count(request):
    """
    GET /api/messages/unread-count
    Total unread messages for the logged-in parent/teacher, across every
    conversation (not just one child). Does NOT mark anything as read —
    it's only used to light up the "Messages" nav badge. Powers the
    periodic badge refresh in base.html.
    """
    payload, err = _messaging_auth(request)
    if err:
        return err

    role = payload['role']
    uid = payload['sub']
    opposite_role = 'teacher' if role == 'parent' else 'parent'

    if role == 'parent':
        child_ids = Child.objects.filter(
            Q(parent_id=uid) | Q(parent_email__iexact=Parent.objects.filter(pk=uid).values_list('email', flat=True).first() or '')
        ).values_list('id', flat=True)
    else:
        child_ids = Child.objects.filter(teacher_id=uid).values_list('id', flat=True)

    count = Message.objects.filter(
        child_id__in=child_ids, sender_role=opposite_role, is_read=False
    ).count()

    return JsonResponse({'unread_count': count})


def check_child_generation_eligibility(child: Child) -> Tuple[bool, str]:
    """Checks daily quota / cooldown. Bypassed when testing."""
    if not are_story_thresholds_enabled():
        return True, ""  # Disabled for testing

    now = timezone.now()
    recent = AIStoryJob.objects.filter(
        child=child,
        created_at__gte=now - timedelta(days=1),
        status__in=[AIStoryJob.STATUS_RUNNING, AIStoryJob.STATUS_DONE]
    )
    if recent.count() >= 3:
        return False, "Daily limit reached (max 3 stories per day)."

    last_job = recent.order_by('-created_at').first()
    if last_job and (now - last_job.created_at).total_seconds() < 300:
        return False, "Please wait 5 minutes before generating another story."

    return True, ""


def process_ai_story_job(job_id: int):
    """Background worker thread for generating stories."""
    try:
        job = AIStoryJob.objects.get(pk=job_id)
        job.status = AIStoryJob.STATUS_RUNNING
        job.save(update_fields=['status', 'updated_at'])

        if job.grade == 1:
            # Keep the API entry point on the same CAPS RAG and assessment path
            # as the Grade 1 learner-facing generator.
            from lessons.views import create_ai_story_for_grade
            lesson = create_ai_story_for_grade(job.child)
            job.lesson = lesson
            job.status = AIStoryJob.STATUS_DONE
            job.save(update_fields=['status', 'lesson', 'updated_at'])
            logger.info(f"AIStoryJob #{job_id} succeeded. Lesson #{lesson.id} created.")
            return

        # 1. RAG retrieval
        recent_titles = list(
            Lesson.objects.filter(grade=job.grade)
            .order_by('-created_at')
            .values_list('title', flat=True)[:10]
        )
        blueprint, vocabulary, expected_activities = retrieve_grade4_context(recent_titles)

        # 2. Build prompt
        prompt = grade4_prompt_context(
            blueprint=blueprint,
            vocabulary=vocabulary,
            recent_titles=recent_titles,
            learner_token=f"child-{job.child.pk}"
        )

        # 3. Call Gemini
        raw_story = call_gemini_for_story(prompt)

        # 4. Self-healing repair
        validated_story = validate_and_repair_grade4_story(
            story=raw_story,
            retrieved_vocabulary=vocabulary,
            expected_activity_types=expected_activities
        )

        # 5. Save lesson
        lesson = save_grade4_lesson(story=validated_story, blueprint=blueprint, grade=job.grade)

        # 6. Complete
        job.lesson = lesson
        job.status = AIStoryJob.STATUS_DONE
        job.save(update_fields=['status', 'lesson', 'updated_at'])
        logger.info(f"AIStoryJob #{job_id} succeeded. Lesson #{lesson.id} created.")

    except Exception as exc:
        logger.exception(f"AIStoryJob #{job_id} failed: {exc}")
        AIStoryJob.objects.filter(pk=job_id).update(
            status=AIStoryJob.STATUS_ERROR,
            error_message=str(exc),
            updated_at=timezone.now()
        )


@require_http_methods(["POST"])
def request_ai_story(request, child_id: int):
    """Starts the background story generation."""
    try:
        child = Child.objects.get(pk=child_id)
    except Child.DoesNotExist:
        return JsonResponse({"error": "Child not found"}, status=404)

    eligible, reason, _ = check_ai_story_eligibility(child, child.grade)
    if not eligible:
        return JsonResponse({"error": reason}, status=429)

    allowed, reason = check_child_generation_eligibility(child)
    if not allowed:
        return JsonResponse({"error": reason, "threshold_exceeded": True}, status=429)

    # Return existing job if already in progress
    in_flight = AIStoryJob.objects.filter(
        child=child,
        status__in=[AIStoryJob.STATUS_PENDING, AIStoryJob.STATUS_RUNNING]
    ).first()
    if in_flight:
        return JsonResponse({"job_id": in_flight.id, "status": in_flight.status})

    job = AIStoryJob.objects.create(
        child=child,
        grade=child.grade or 4,
        status=AIStoryJob.STATUS_PENDING
    )

    # Start generation in background thread
    threading.Thread(target=process_ai_story_job, args=(job.id,), daemon=True).start()

    return JsonResponse({"job_id": job.id, "status": job.status}, status=202)


@require_http_methods(["GET"])
def get_ai_story_status(request, job_id: int):
    """Polling endpoint for the frontend."""
    try:
        job = AIStoryJob.objects.select_related('lesson').get(pk=job_id)
    except AIStoryJob.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    data = {
        "job_id": job.id,
        "status": job.status,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }

    if job.status == AIStoryJob.STATUS_DONE and job.lesson:
        data["lesson"] = {
            "id": job.lesson.id,
            "title": job.lesson.title,
            "grade": job.lesson.grade,
            "character_description": job.lesson.character_description,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "highlighted_words": p.highlighted_words,
                    "illustration_prompt": p.illustration_prompt,
                }
                for p in job.lesson.pages.all()
            ],
            "activities_count": job.lesson.activities.count(),
        }

    return JsonResponse(data)
