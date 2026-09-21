"""
Frontend views for the SGILA web app.

The API module exposes JSON endpoints. These views render the role-aware
application screens described in the supplied wireframes and data-flow docs.
"""
import hashlib
import json
import random
import re
import secrets
import threading
import time
import urllib.parse
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from uuid import uuid4

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from api.models import (
    AccountActionOTP,
    AIStoryJob,
    CauseEffectPair,
    Child,
    ComprehensionQuestion,
    FeelingsQuestion,
    Grade4ActivityProgress,
    GradeHistory,
    InferenceQuestion,
    Lesson,
    Message,
    Parent,
    PredictionQuestion,
    Progress,
    PronunciationWord,
    ReadingActivity,
    ReadingActivityResponse,
    SequencingActivity,
    SpellingActivity,
    StoryPage,
    Teacher,
    TeacherClass,
    ThemeQuestion,
    VisualActivityItem,
    VocabularyQuestion,
    WrittenResponsePrompt,
    generate_class_code,
    OTPToken,
    PasswordResetToken,
    Subscription,
    PackageCode,
    capitalize_first,
    current_school_year,
    title_case,
)
from api.account_access import child_access_status, subscription_allows_children
from api.reporting import aggregate_rows, rows_for_record, rows_from_scores


def password_matches(raw, stored):
    if check_password(raw, stored):
        return True
    return stored == hashlib.sha256(raw.encode()).hexdigest()


def set_account_session(request, role, account, child=None):
    request.session.flush()
    request.session['account_role'] = role
    request.session['account_id'] = account.id
    request.session['account_name'] = getattr(account, 'full_name', getattr(account, 'name', 'Friend'))
    if child:
        request.session['child_id'] = child.id
        request.session['child_name'] = child.name
        request.session['child_grade'] = child.grade


def account_trial_expired(account):
    """True if this Parent/Teacher's own subscription has run past its free trial."""
    subscription = getattr(account, 'subscription', None)
    return bool(subscription and subscription.is_trial_expired)


def learner_trial_expired(child):
    """A learner's access rides on their parent's subscription: if the parent's
    free trial has lapsed, the child is blocked too. School-linked learners
    (no parent account, added via a teacher/class code) aren't gated this way —
    their access follows the school's package-code subscription instead.
    """
    if not child.parent_id:
        return False
    return account_trial_expired(child.parent)


def payment_due_response(request, context=None):
    """Renders the 'payment due' screen in place of blocked content."""
    return render(request, 'payment_due.html', context or {})


REACTIVATION_CHALLENGE_SECONDS = 15 * 60
REACTIVATION_RESEND_SECONDS = 60


def begin_account_reactivation(request, role, account):
    request.session.flush()
    request.session['pending_reactivation_role'] = role
    request.session['pending_reactivation_account_id'] = account.id
    request.session['pending_reactivation_verified_at'] = int(timezone.now().timestamp())


def clear_account_reactivation(request):
    request.session.pop('pending_reactivation_role', None)
    request.session.pop('pending_reactivation_account_id', None)
    request.session.pop('pending_reactivation_verified_at', None)
    request.session.pop('reactivation_token_id', None)
    request.session.modified = True


def pending_reactivation_account(request):
    """Return (role, account) for a reactivation in progress, or (None, None).

    Shared by parent and teacher self-reactivation — both go through the same
    'confirm the OTP we emailed you' screen.
    """
    role = request.session.get('pending_reactivation_role')
    account_id = request.session.get('pending_reactivation_account_id')
    verified_at = request.session.get('pending_reactivation_verified_at')
    try:
        challenge_age = timezone.now().timestamp() - int(verified_at)
    except (TypeError, ValueError):
        challenge_age = REACTIVATION_CHALLENGE_SECONDS + 1
    if not role or not account_id or challenge_age > REACTIVATION_CHALLENGE_SECONDS:
        clear_account_reactivation(request)
        return None, None
    model = {'parent': Parent, 'teacher': Teacher}.get(role)
    if not model:
        clear_account_reactivation(request)
        return None, None
    account = model.objects.filter(pk=account_id, is_active=False).first()
    if not account:
        clear_account_reactivation(request)
        return None, None
    return role, account


def masked_email(email):
    local, domain = email.split('@', 1)
    return local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'


def learner_required(request):
    child_id = request.session.get('child_id')
    if not child_id:
        messages.error(request, 'Please sign in as a learner first.')
        return None, redirect('/login?role=learner')
    child = get_object_or_404(Child, id=child_id)
    # Self-heals the stored age against date_of_birth on every learner page load,
    # so it rolls over on the child's birthday without needing a scheduled task.
    child.refresh_age_if_stale()
    if learner_trial_expired(child):
        return child, payment_due_response(request, {'role': 'learner', 'child': child})
    return child, None


def activity_choices_for(lesson):
    """Return the learner-facing activity menu for a lesson."""
    base = f'/lessons/{lesson.id}'
    choices = [{'label': 'Read the story', 'url': f'{base}/story'}]
    if lesson.grade == 3:
        choices.append({
            'label': 'Grade 3 activities',
            'url': f'{base}/activities',
        })
    elif lesson.grade == 4:
        choices.extend([
            {'label': 'Comprehension', 'url': f'{base}/questions'},
            {'label': 'Vocabulary', 'url': f'{base}/vocabulary'},
            {'label': 'Sequencing', 'url': f'{base}/sequencing'},
            {'label': 'Inference', 'url': f'{base}/inference'},
            {'label': 'Prediction', 'url': f'{base}/prediction'},
            {'label': 'Feelings', 'url': f'{base}/feelings'},
            {'label': 'Cause and effect', 'url': f'{base}/cause-effect'},
            {'label': 'Main lesson', 'url': f'{base}/theme'},
            {'label': 'Written response', 'url': f'{base}/written-response'},
        ])
    else:
        choices.extend([
            {'label': 'Comprehension', 'url': f'{base}/questions'},
            {'label': 'Visual matching', 'url': f'{base}/visual-activity'},
            {'label': 'Pronunciation', 'url': f'{base}/pronunciation'},
            {'label': 'Spelling', 'url': f'{base}/spelling'},
        ])
    return choices


def activity_resume_url(request, child, lesson):
    """Return the best saved destination when a learner reopens a story."""
    answers = request.session.get(f'lesson_{lesson.id}_reading_activity_answers', {})
    answered_ids = {
        str(key).removeprefix('activity-')
        for key in answers
        if str(key).startswith('activity-')
    }
    activities = list(lesson.reading_activities.order_by('order', 'id'))
    for index, activity in enumerate(activities):
        if str(activity.id) not in answered_ids:
            return f'/lessons/{lesson.id}/questions?activity_index={index}'

    paused_url = (child.paused_activities or {}).get(str(lesson.id))
    if paused_url:
        return paused_url
    return None


def activity_score_summary(request, lesson):
    """Summarise the in-progress attempt stored in the learner session."""
    prefix = f'lesson_{lesson.id}_'
    if lesson.grade == 4:
        fields = [
            ('comprehension_score', 'comprehension_total', lesson.questions.count()),
            ('seq_score', 'seq_total', 1),
            ('inference_score', 'inference_total', lesson.inference_questions.count()),
            ('feelings_score', 'feelings_total', lesson.feelings_questions.count()),
            ('ce_score', 'ce_total', lesson.cause_effect_pairs.count()),
            ('theme_score', 'theme_total', 1),
        ]
    else:
        fields = [
            ('comprehension_score', 'comprehension_total', lesson.questions.count()),
            ('visual_score', 'visual_total', lesson.visual_items.count()),
            ('spelling_score', 'spelling_total', lesson.spelling_activities.count()),
        ]
    score = sum(int(request.session.get(prefix + score_key, 0)) for score_key, _, _ in fields)
    possible = sum(int(request.session.get(prefix + total_key, default)) for _, total_key, default in fields)
    return score, possible


def parse_grades(grades_taught):
    grades = []
    for raw_grade in (grades_taught or '').replace(';', ',').split(','):
        raw_grade = raw_grade.strip()
        if raw_grade.isdigit():
            grades.append(int(raw_grade))
    return grades


def unique_code_for(model):
    while True:
        code = generate_class_code()
        if not model.objects.filter(class_code=code).exists():
            return code


def normalize_child_username(raw_value):
    username = re.sub(r'[^A-Za-z]', '', (raw_value or '').strip())
    return capitalize_first(username[:40])


def unique_child_username(raw_value):
    base = normalize_child_username(raw_value) or 'learner'
    candidate = base[:40]
    suffix = 2
    while Child.objects.filter(username=candidate).exists():
        suffix_text = f'_{suffix}'
        candidate = f'{base[:40 - len(suffix_text)]}{suffix_text}'
        suffix += 1
    return candidate


def ensure_teacher_codes(teacher):
    if not teacher.class_code:
        teacher.class_code = unique_code_for(Teacher)
        teacher.save(update_fields=['class_code'])

    grades = parse_grades(teacher.grades_taught) or [1]
    for grade in grades:
        teacher_class, _ = TeacherClass.objects.get_or_create(
            teacher=teacher,
            grade=grade,
            defaults={'name': f'Grade {grade}'},
        )
        changed = False
        if not teacher_class.name:
            teacher_class.name = f'Grade {grade}'
            changed = True
        if not teacher_class.class_code:
            teacher_class.class_code = unique_code_for(TeacherClass)
            changed = True
        if changed:
            teacher_class.save()

    return teacher.classes.all().order_by('grade', 'name')


def resolve_class_code(raw_code):
    code = (raw_code or '').strip().upper()
    if not code:
        return None, None

    teacher_class = TeacherClass.objects.filter(class_code__iexact=code).select_related('teacher').first()
    if teacher_class:
        return teacher_class.teacher, teacher_class

    teacher = Teacher.objects.filter(class_code__iexact=code).first()
    if teacher:
        ensure_teacher_codes(teacher)
        return teacher, None

    return None, None


def link_child_to_class(child, raw_code):
    teacher, teacher_class = resolve_class_code(raw_code)
    if teacher:
        child.teacher = teacher
        child.teacher_class = teacher_class
        if not child.school_name:
            child.school_name = teacher.school_name
    return bool(teacher)


def mark_grade_confirmed_at_registration(child):
    """Registering a child counts as confirming their grade for this school year.

    Every year after this one, the parent/teacher dashboard will prompt for an
    explicit confirmation instead of assuming the child moved up a grade — see
    Child.needs_grade_confirmation().
    """
    child.grade_confirmed_year = current_school_year()
    child.save(update_fields=['grade_confirmed_year'])
    GradeHistory.objects.update_or_create(
        child=child,
        year=current_school_year(),
        defaults={'grade': child.grade, 'confirmed_by': GradeHistory.REGISTRATION},
    )


def teacher_can_view_child(teacher, child):
    if child.teacher_id == teacher.id:
        return True
    if teacher.school_name.strip().lower() != child.school_name.strip().lower():
        return False
    grades = parse_grades(teacher.grades_taught)
    return not grades or child.grade in grades


def user_can_view_child(request, child):
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')

    if role == 'learner':
        return request.session.get('child_id') == child.id

    if role == 'parent' and account_id:
        parent = Parent.objects.filter(id=account_id).first()
        return bool(parent and (child.parent_id == parent.id or child.parent_email.lower() == parent.email.lower()))

    if role == 'teacher' and account_id:
        teacher = Teacher.objects.filter(id=account_id).first()
        return bool(teacher and teacher_can_view_child(teacher, child))

    return False


def redirect_after_forbidden(request):
    role = request.session.get('account_role')
    if role == 'parent':
        return redirect('/parent/dashboard')
    if role == 'teacher':
        return redirect('/teacher/dashboard')
    if role == 'learner':
        grade = request.session.get('child_grade')
        return redirect(f'/grade/{grade}' if grade else '/')
    return redirect('/login')


def terms_page(request):
    """Renders the Sgila Terms & Conditions page."""
    return render(request, 'terms.html')


def welcome(request):
    return render(request, 'welcome.html')


def ui_flow_diagram(request):
    return render(request, 'ui_flow_diagram.html')


def download_ui_flow_pdf(request):
    pdf_path = Path(settings.BASE_DIR) / 'static' / 'diagrams' / 'sgila_ui_flow_orderly.pdf'
    if not pdf_path.exists():
        raise Http404('UI flow PDF has not been generated yet.')
    return FileResponse(
        pdf_path.open('rb'),
        as_attachment=True,
        filename='sgila_ui_flow_orderly.pdf',
        content_type='application/pdf',
    )


@require_http_methods(["GET", "POST"])
def register_page(request):
    role = request.POST.get('role') or request.GET.get('role', 'parent')
    if role not in ['parent', 'teacher']:
        role = 'parent'

    if request.method == 'POST':
        if role == 'teacher':
            return register_teacher(request)
        return register_parent(request)

    return render(request, 'register.html', {'role': role})


def register_learner(request):
    data = request.POST
    parent_email = data['parent_email'].strip().lower()
    username = unique_child_username(data.get('username') or parent_email.split('@')[0])
    if Child.objects.filter(parent_email=parent_email, username__isnull=True).exists():
        messages.error(request, 'That email is already registered.')
        return render(request, 'register.html', {'role': 'learner'})

    grade = int(data['grade'])
    class_code = data.get('class_code', '').strip()
    teacher = teacher_class = None
    if class_code:
        teacher, teacher_class = resolve_class_code(class_code)
        if not teacher:
            messages.error(request, 'That teacher class code was not found.')
            return render(request, 'register.html', {'role': 'learner'})

    child = Child.objects.create(
        username=username,
        first_name=data['child_name'].strip(),
        name=data['child_name'].strip(),
        age=int(data['age']),
        grade=grade,
        school_name=data.get('school_name', '').strip() or (teacher.school_name if teacher else ''),
        parent_email=parent_email,
        password=make_password(data['password']),
        teacher=teacher,
        teacher_class=teacher_class,
    )
    mark_grade_confirmed_at_registration(child)
    set_account_session(request, 'learner', child, child)
    return redirect(f'/grade/{child.grade}')


def register_parent(request):
    data = request.POST
    email = data['email'].strip().lower()
    full_name = title_case(data.get('full_name'))

    if Parent.objects.filter(email=email).exists():
        messages.error(request, 'That parent email is already registered.')
        return render(request, 'register.html', {'role': 'parent'})

    # Invalidate any previous unused OTPs for this email
    OTPToken.objects.filter(email=email, role='parent', is_used=False).delete()

    code = str(random.randint(100000, 999999))
    pending_data = {
        'role': 'parent',
        'full_name': full_name,
        'email': email,
        'phone': data.get('phone', '').strip(),
        'password': data['password'],
        'accepted_popia': bool(data.get('accepted_popia')),
    }
    otp = OTPToken.objects.create(
        email=email,
        role='parent',
        code=code,
        pending_data=json.dumps(pending_data),
    )
    if settings.DEBUG:
        print(f'\n[SGILA OTP] Parent verification code for {email}: {code}\n', flush=True)

    # Send OTP email
    subject = "Your SGILA verification code"
    message = (
        f"Hi {full_name},\n\n"
        f"Your SGILA verification code is: {code}\n\n"
        f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
        f"— The SGILA Team"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

    local, domain = email.split('@', 1)
    masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'

    return render(request, 'verify_otp.html', {
        'otp_session': str(otp.id),
        'masked_email': masked,
        'role': 'parent',
    })


def register_teacher(request):
    data = request.POST
    email = data['email'].strip().lower()
    full_name = title_case(data.get('full_name'))

    if Teacher.objects.filter(email=email).exists():
        messages.error(request, 'That teacher email is already registered.')
        return render(request, 'register.html', {'role': 'teacher'})

    # Invalidate any previous unused OTPs for this email
    OTPToken.objects.filter(email=email, role='teacher', is_used=False).delete()

    code = str(random.randint(100000, 999999))
    pending_data = {
        'role': 'teacher',
        'full_name': full_name,
        'email': email,
        'school_name': title_case(data.get('school_name')),
        'grades_taught': ','.join(data.getlist('grades_taught')) or data.get('grades_taught', ''),
        'phone': data.get('phone', '').strip(),
        'password': data['password'],
        'accepted_popia': bool(data.get('accepted_popia')),
    }
    otp = OTPToken.objects.create(
        email=email,
        role='teacher',
        code=code,
        pending_data=json.dumps(pending_data),
    )
    if settings.DEBUG:
        print(f'\n[SGILA OTP] Teacher verification code for {email}: {code}\n', flush=True)

    subject = "Your SGILA verification code"
    message = (
        f"Hi {full_name},\n\n"
        f"Your SGILA verification code is: {code}\n\n"
        f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
        f"— The SGILA Team"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

    local, domain = email.split('@', 1)
    masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'

    return render(request, 'verify_otp.html', {
        'otp_session': str(otp.id),
        'masked_email': masked,
        'role': 'teacher',
    })


@require_http_methods(["GET", "POST"])
def login_page(request):
    role = request.POST.get('role') or request.GET.get('role', 'learner')
    if role not in ['learner', 'parent', 'teacher']:
        role = 'learner'

    if request.method == 'POST':
        email = request.POST['email'].strip().lower()
        password = request.POST['password']

        model = {'learner': Child, 'parent': Parent, 'teacher': Teacher}[role]
        if role == 'learner':
            account = Child.objects.filter(Q(username__iexact=email) | Q(parent_email__iexact=email)).first()
        else:
            try:
                account = model.objects.get(email=email)
            except model.DoesNotExist:
                account = None

        if account and password_matches(password, account.password):
            if role == 'learner':
                allowed, reason = child_access_status(account)
                if not allowed:
                    request.session.flush()
                    return redirect(f'/account-access?reason={reason}')
                set_account_session(request, role, account, account)
                return redirect(f'/grade/{account.grade}')
            if role == 'parent' and not account.is_active:
                begin_account_reactivation(request, 'parent', account)
                return redirect('/account/reactivate')
            if role == 'teacher' and not account.is_active:
                begin_account_reactivation(request, 'teacher', account)
                return redirect('/account/reactivate')
            set_account_session(request, role, account)
            return redirect(f'/{role}/dashboard')

        if role == 'learner':
            messages.error(request, 'Incorrect username or password.')
        else:
            messages.error(request, 'Incorrect email or password.')

    return render(request, 'login.html', {'role': role})


def logout_view(request):
    request.session.flush()
    return redirect('/')


@require_http_methods(['GET'])
def account_access_page(request):
    reason = request.GET.get('reason', '')
    content = {
        'parent_deactivated': {
            'title': 'Your SGILA access is paused',
            'message': 'This learner profile is linked to a deactivated parent account. Ask your parent to sign in and reactivate their account.',
        },
        'teacher_deactivated': {
            'title': 'Your SGILA access is paused',
            'message': 'This account has been deactivated. Sign in again to start reactivating it.',
        },
        'learner_deactivated': {
            'title': 'This learner profile is paused',
            'message': 'A parent has paused this learner profile. Ask your parent to reactivate it from their dashboard.',
        },
        'subscription_inactive': {
            'title': 'Your learning plan is paused',
            'message': 'This learner profile needs an active SGILA plan. Ask your parent to sign in and update the family plan.',
        },
        'learner_not_found': {
            'title': 'We could not find this learner profile',
            'message': 'Ask your parent or teacher to check the learner account details.',
        },
    }.get(reason, {
        'title': 'SGILA access is paused',
        'message': 'Ask your parent to sign in and check the account.',
    })
    return render(request, 'account_access.html', content)


@require_http_methods(['POST'])
def parent_deactivate_account(request):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')

    parent = get_object_or_404(Parent, id=request.session.get('account_id'))
    password = request.POST.get('password', '')
    if not password_matches(password, parent.password):
        messages.error(request, 'Your password was incorrect. The account was not deactivated.')
        return redirect('/parent/dashboard')

    cancel_subscription = request.POST.get('cancel_subscription') == 'on'
    with transaction.atomic():
        parent = Parent.objects.select_for_update().get(pk=parent.pk)
        if parent.is_active:
            parent.is_active = False
            parent.deactivated_at = timezone.now()
            parent.auth_version += 1
            parent.save(update_fields=['is_active', 'deactivated_at', 'auth_version'])
        # Sweep every currently-active child along with the parent. Children
        # already paused individually (deactivated_reason='manual') are left
        # untouched, and they stay off even after the parent reactivates.
        Child.objects.filter(
            Q(parent=parent) | Q(parent_email__iexact=parent.email),
            is_active=True,
        ).update(
            is_active=False,
            deactivated_at=timezone.now(),
            deactivated_reason=Child.DEACTIVATED_PARENT_CASCADE,
        )
        AccountActionOTP.objects.filter(parent=parent, is_used=False).update(is_used=True)
        if cancel_subscription:
            Subscription.objects.filter(parent=parent).update(
                status='cancelled',
                updated_at=timezone.now(),
            )

    request.session.flush()
    messages.success(request, 'Your SGILA account is deactivated. Your records have been retained for possible reactivation.')
    return redirect('/login?role=parent')


@require_http_methods(['POST'])
def teacher_deactivate_account(request):
    if request.session.get('account_role') != 'teacher':
        return redirect('/login?role=teacher')

    teacher = get_object_or_404(Teacher, id=request.session.get('account_id'))
    password = request.POST.get('password', '')
    if not password_matches(password, teacher.password):
        messages.error(request, 'Your password was incorrect. The account was not deactivated.')
        return redirect('/teacher/dashboard')

    cancel_subscription = request.POST.get('cancel_subscription') == 'on'
    with transaction.atomic():
        teacher = Teacher.objects.select_for_update().get(pk=teacher.pk)
        if teacher.is_active:
            teacher.is_active = False
            teacher.deactivated_at = timezone.now()
            teacher.auth_version += 1
            teacher.save(update_fields=['is_active', 'deactivated_at', 'auth_version'])
        AccountActionOTP.objects.filter(teacher=teacher, is_used=False).update(is_used=True)
        # The teacher's classes stay put (learners keep their history), but they
        # get flagged so the school knows those classes need a new teacher.
        TeacherClass.objects.filter(teacher=teacher).update(needs_new_teacher=True)
        if cancel_subscription:
            Subscription.objects.filter(teacher=teacher).update(
                status='cancelled',
                updated_at=timezone.now(),
            )

    request.session.flush()
    messages.success(request, 'Your SGILA account is deactivated. Your records have been retained for possible reactivation.')
    return redirect('/login?role=teacher')


@require_http_methods(['GET', 'POST'])
def reactivate_account(request):
    role, account = pending_reactivation_account(request)
    if not account:
        messages.error(request, 'Sign in with the deactivated account to start reactivation.')
        return redirect('/login')

    otp_field = {'parent': 'parent', 'teacher': 'teacher'}[role]
    reactivate_action = {
        'parent': AccountActionOTP.REACTIVATE_PARENT,
        'teacher': AccountActionOTP.REACTIVATE_TEACHER,
    }[role]

    action = request.POST.get('action', '')
    if request.method == 'POST' and action in {'send', 'resend'}:
        latest = AccountActionOTP.objects.filter(
            **{otp_field: account},
            action=reactivate_action,
        ).first()
        if latest and (timezone.now() - latest.created_at).total_seconds() < REACTIVATION_RESEND_SECONDS:
            if latest.can_attempt:
                request.session['reactivation_token_id'] = latest.id
                redirect_url = '/account/reactivate?sent=1'
            else:
                request.session.pop('reactivation_token_id', None)
                redirect_url = '/account/reactivate'
            messages.info(request, 'A code was sent recently. Please wait one minute before requesting another.')
            return redirect(redirect_url)

        AccountActionOTP.objects.filter(
            **{otp_field: account},
            action=reactivate_action,
            is_used=False,
        ).update(is_used=True)
        code = f'{secrets.randbelow(900000) + 100000:06d}'
        token = AccountActionOTP.objects.create(
            **{otp_field: account},
            action=reactivate_action,
            code_hash=make_password(code),
        )
        try:
            send_mail(
                'Reactivate your SGILA account',
                (
                    f'Hi {account.full_name},\n\n'
                    f'Your SGILA reactivation code is: {code}\n\n'
                    'This code expires in 10 minutes. Do not share it with anyone.\n\n'
                    'If you did not request this, you can ignore this email.\n\n'
                    '- The SGILA Team'
                ),
                settings.DEFAULT_FROM_EMAIL,
                [account.email],
                fail_silently=False,
            )
        except Exception:
            token.delete()
            messages.error(request, 'We could not send the email right now. Your account is still deactivated; please try again.')
            return redirect('/account/reactivate')

        request.session['reactivation_token_id'] = token.id
        messages.success(request, 'A reactivation code has been sent to your email.')
        return redirect('/account/reactivate?sent=1')

    if request.method == 'POST' and action == 'verify':
        token_id = request.session.get('reactivation_token_id')
        code = request.POST.get('code', '').strip()
        with transaction.atomic():
            token = AccountActionOTP.objects.select_for_update().filter(
                pk=token_id,
                **{otp_field: account},
                action=reactivate_action,
            ).first()
            if not token or not token.can_attempt:
                messages.error(request, 'That code is expired or no longer valid. Request a new code.')
                return redirect('/account/reactivate')
            if not check_password(code, token.code_hash):
                token.attempts += 1
                if token.attempts >= AccountActionOTP.MAX_ATTEMPTS:
                    token.is_used = True
                token.save(update_fields=['attempts', 'is_used'])
                remaining = max(0, AccountActionOTP.MAX_ATTEMPTS - token.attempts)
                messages.error(request, f'Incorrect code. {remaining} attempt(s) remaining.')
                return redirect('/account/reactivate?sent=1')

            token.is_used = True
            token.save(update_fields=['is_used'])
            model = {'parent': Parent, 'teacher': Teacher}[role]
            account = model.objects.select_for_update().get(pk=account.pk)
            account.is_active = True
            account.deactivated_at = None
            account.auth_version += 1
            account.save(update_fields=['is_active', 'deactivated_at', 'auth_version'])
            if role == 'teacher':
                TeacherClass.objects.filter(teacher=account).update(needs_new_teacher=False)
            AccountActionOTP.objects.filter(**{otp_field: account}, is_used=False).update(is_used=True)

        clear_account_reactivation(request)
        set_account_session(request, role, account)
        if role == 'teacher':
            messages.success(request, 'Your SGILA account is active again.')
            return redirect('/teacher/dashboard')
        if subscription_allows_children(account):
            messages.success(request, 'Your SGILA account and learner access are active again.')
            return redirect('/parent/dashboard')
        messages.warning(request, 'Your account is active again. Choose or reactivate a plan to restore learner access.')
        return redirect('/subscription')

    token_id = request.session.get('reactivation_token_id')
    token = AccountActionOTP.objects.filter(
        pk=token_id,
        **{otp_field: account},
        is_used=False,
    ).first()
    return render(request, 'reactivate_account.html', {
        'masked_email': masked_email(account.email),
        'otp_sent': bool(token and token.can_attempt),
    })


@require_http_methods(["GET", "POST"])
def verify_otp_page(request):
    """
    Web view for OTP email verification after parent/teacher registration.
    GET  — show the verify_otp.html form (otp_session from query string)
    POST — handle verify or resend actions
    """
    otp_session = request.POST.get('otp_session') or request.GET.get('session', '')
    action = request.POST.get('action', 'verify')

    if request.method == 'POST':
        if action == 'resend':
            try:
                old_otp = OTPToken.objects.get(id=otp_session, is_used=False)
            except OTPToken.DoesNotExist:
                messages.error(request, 'Verification session not found. Please register again.')
                return redirect('/register')

            pending = json.loads(old_otp.pending_data)
            full_name = pending.get('full_name', 'there')
            old_otp.is_used = True
            old_otp.save()

            new_code = str(random.randint(100000, 999999))
            new_otp = OTPToken.objects.create(
                email=old_otp.email,
                role=old_otp.role,
                code=new_code,
                pending_data=old_otp.pending_data,
            )
            if settings.DEBUG:
                print(f'\n[SGILA OTP] Resent verification code for {old_otp.email}: {new_code}\n', flush=True)
            subject = "Your SGILA verification code"
            message = (
                f"Hi {full_name},\n\n"
                f"Your new SGILA verification code is: {new_code}\n\n"
                f"This code expires in 10 minutes.\n\n"
                f"— The SGILA Team"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [old_otp.email], fail_silently=False)
            messages.success(request, 'A new code has been sent to your email.')

            local, domain = old_otp.email.split('@', 1)
            masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
            return render(request, 'verify_otp.html', {
                'otp_session': str(new_otp.id),
                'masked_email': masked,
                'role': old_otp.role,
            })

        # action == 'verify'
        code = request.POST.get('code', '').strip()
        try:
            otp = OTPToken.objects.get(id=otp_session, is_used=False)
        except OTPToken.DoesNotExist:
            messages.error(request, 'Invalid or expired verification session. Please register again.')
            return redirect('/register')

        if otp.is_expired():
            messages.error(request, 'Your code has expired. Please register again to get a new one.')
            return redirect('/register')

        if otp.code != code:
            messages.error(request, 'Incorrect code. Please try again.')
            local, domain = otp.email.split('@', 1)
            masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
            return render(request, 'verify_otp.html', {
                'otp_session': otp_session,
                'masked_email': masked,
                'role': otp.role,
            })

        otp.is_used = True
        otp.save()

        pending = json.loads(otp.pending_data)
        role = otp.role

        if role == 'parent':
            account = Parent.objects.create(
                full_name=pending.get('full_name', '').strip(),
                email=otp.email,
                phone=pending.get('phone', '').strip(),
                password=make_password(pending.get('password', '')),
                accepted_popia=bool(pending.get('accepted_popia')),
            )
            set_account_session(request, 'parent', account)
            messages.success(request, 'Email verified. Welcome to SGILA!')
            return redirect('/parent/dashboard')
        else:
            account = Teacher.objects.create(
                full_name=pending.get('full_name', '').strip(),
                email=otp.email,
                school_name=pending.get('school_name', '').strip(),
                grades_taught=pending.get('grades_taught', ''),
                phone=pending.get('phone', '').strip(),
                password=make_password(pending.get('password', '')),
                accepted_popia=bool(pending.get('accepted_popia')),
                class_code=unique_code_for(Teacher),
            )
            ensure_teacher_codes(account)
            set_account_session(request, 'teacher', account)
            messages.success(request, f'Email verified. Share class code {account.class_code} with learners.')
            return redirect('/teacher/dashboard')

    # GET — show the form
    try:
        otp = OTPToken.objects.get(id=otp_session, is_used=False)
        local, domain = otp.email.split('@', 1)
        masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
        return render(request, 'verify_otp.html', {
            'otp_session': otp_session,
            'masked_email': masked,
            'role': otp.role,
        })
    except OTPToken.DoesNotExist:
        messages.error(request, 'Verification session not found. Please register again.')
        return redirect('/register')


@require_http_methods(["GET", "POST"])
def forgot_password_page(request):
    """
    Forgot Password — Step 1 web view.
    GET:  Show the form asking for email + role.
    POST: Validate, create a PasswordResetToken, send email with reset link.
    """
    import secrets as _secrets

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', '').strip()

        if role not in ('parent', 'teacher'):
            messages.error(request, 'Please select a valid role.')
            return render(request, 'forgot_password.html', {'role': role})
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'forgot_password.html', {'role': role})

        model = Parent if role == 'parent' else Teacher
        account = model.objects.filter(email=email).first()

        if account:
            # Invalidate old tokens for this email/role
            PasswordResetToken.objects.filter(email=email, role=role, is_used=False).update(is_used=True)

            token = _secrets.token_urlsafe(48)
            PasswordResetToken.objects.create(email=email, role=role, token=token)

            site_url = settings.SITE_URL.rstrip('/')
            reset_url = f"{site_url}/reset-password?token={token}&role={role}"
            subject = "Reset your SGILA password"
            body = (
                f"Hi {account.full_name},\n\n"
                f"We received a request to reset your SGILA password.\n\n"
                f"Click the link below to choose a new password:\n"
                f"{reset_url}\n\n"
                f"This link expires in 30 minutes. If you did not request this, "
                f"you can safely ignore this email.\n\n"
                f"— The SGILA Team"
            )
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            except Exception:
                pass

        # Always show the same success page to avoid revealing whether an account exists
        return render(request, 'forgot_password.html', {'sent': True, 'role': role})

    role = request.GET.get('role', 'parent')
    return render(request, 'forgot_password.html', {'role': role})


@require_http_methods(["GET", "POST"])
def reset_password_page(request):
    """
    Forgot Password — Step 2 web view.
    GET:  Show the new-password form (token + role from query string).
    POST: Validate token, update password, redirect to login.
    """
    token_value = request.GET.get('token') or request.POST.get('token', '')
    role = request.GET.get('role') or request.POST.get('role', '')

    if not token_value or role not in ('parent', 'teacher'):
        messages.error(request, 'Invalid or missing reset link. Please request a new one.')
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'reset_password.html', {'token': token_value, 'role': role})

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'reset_password.html', {'token': token_value, 'role': role})

        try:
            reset_token = PasswordResetToken.objects.get(token=token_value, role=role, is_used=False)
        except PasswordResetToken.DoesNotExist:
            messages.error(request, 'This reset link is invalid or has already been used.')
            return redirect('/forgot-password')

        if reset_token.is_expired():
            reset_token.is_used = True
            reset_token.save()
            messages.error(request, 'This reset link has expired. Please request a new one.')
            return redirect('/forgot-password')

        model = Parent if role == 'parent' else Teacher
        account = model.objects.filter(email=reset_token.email).first()
        if not account:
            messages.error(request, 'Account not found.')
            return redirect('/forgot-password')

        account.password = make_password(new_password)
        account.save()
        reset_token.is_used = True
        reset_token.save()

        messages.success(request, 'Your password has been reset. Please sign in.')
        return redirect(f'/login?role={role}')

    # GET — validate the token before showing the form
    try:
        reset_token = PasswordResetToken.objects.get(token=token_value, role=role, is_used=False)
        if reset_token.is_expired():
            reset_token.is_used = True
            reset_token.save()
            messages.error(request, 'This reset link has expired. Please request a new one.')
            return redirect('/forgot-password')
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid or already used reset link. Please request a new one.')
        return redirect('/forgot-password')

    return render(request, 'reset_password.html', {'token': token_value, 'role': role})



    """
    Web view for OTP email verification after parent/teacher registration.
    GET  — show the verify_otp.html form (otp_session from query string)
    POST — handle verify or resend actions
    """
    otp_session = request.POST.get('otp_session') or request.GET.get('session', '')
    action = request.POST.get('action', 'verify')

    if request.method == 'POST':
        if action == 'resend':
            try:
                old_otp = OTPToken.objects.get(id=otp_session, is_used=False)
            except OTPToken.DoesNotExist:
                messages.error(request, 'Verification session not found. Please register again.')
                return redirect('/register')

            pending = json.loads(old_otp.pending_data)
            full_name = pending.get('full_name', 'there')
            old_otp.is_used = True
            old_otp.save()

            new_code = str(random.randint(100000, 999999))
            new_otp = OTPToken.objects.create(
                email=old_otp.email,
                role=old_otp.role,
                code=new_code,
                pending_data=old_otp.pending_data,
            )
            subject = "Your SGILA verification code"
            message = (
                f"Hi {full_name},\n\n"
                f"Your new SGILA verification code is: {new_code}\n\n"
                f"This code expires in 10 minutes.\n\n"
                f"— The SGILA Team"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [old_otp.email], fail_silently=False)
            messages.success(request, 'A new code has been sent to your email.')

            local, domain = old_otp.email.split('@', 1)
            masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
            return render(request, 'verify_otp.html', {
                'otp_session': str(new_otp.id),
                'masked_email': masked,
                'role': old_otp.role,
            })

        # action == 'verify'
        code = request.POST.get('code', '').strip()
        try:
            otp = OTPToken.objects.get(id=otp_session, is_used=False)
        except OTPToken.DoesNotExist:
            messages.error(request, 'Invalid or expired verification session. Please register again.')
            return redirect('/register')

        if otp.is_expired():
            messages.error(request, 'Your code has expired. Please register again to get a new one.')
            return redirect('/register')

        if otp.code != code:
            messages.error(request, 'Incorrect code. Please try again.')
            local, domain = otp.email.split('@', 1)
            masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
            return render(request, 'verify_otp.html', {
                'otp_session': otp_session,
                'masked_email': masked,
                'role': otp.role,
            })

        otp.is_used = True
        otp.save()

        pending = json.loads(otp.pending_data)
        role = otp.role

        if role == 'parent':
            account = Parent.objects.create(
                full_name=pending.get('full_name', '').strip(),
                email=otp.email,
                phone=pending.get('phone', '').strip(),
                password=make_password(pending.get('password', '')),
                accepted_popia=bool(pending.get('accepted_popia')),
            )
            set_account_session(request, 'parent', account)
            messages.success(request, 'Email verified. Welcome to SGILA!')
            return redirect('/parent/dashboard')
        else:
            account = Teacher.objects.create(
                full_name=pending.get('full_name', '').strip(),
                email=otp.email,
                school_name=pending.get('school_name', '').strip(),
                grades_taught=pending.get('grades_taught', ''),
                phone=pending.get('phone', '').strip(),
                password=make_password(pending.get('password', '')),
                accepted_popia=bool(pending.get('accepted_popia')),
                class_code=unique_code_for(Teacher),
            )
            ensure_teacher_codes(account)
            set_account_session(request, 'teacher', account)
            messages.success(request, f'Email verified. Share class code {account.class_code} with learners.')
            return redirect('/teacher/dashboard')

    # GET — show the form
    try:
        otp = OTPToken.objects.get(id=otp_session, is_used=False)
        local, domain = otp.email.split('@', 1)
        masked = local[:2] + '*' * max(3, len(local) - 2) + '@' + domain[:2] + '*****'
        return render(request, 'verify_otp.html', {
            'otp_session': otp_session,
            'masked_email': masked,
            'role': otp.role,
        })
    except OTPToken.DoesNotExist:
        messages.error(request, 'Verification session not found. Please register again.')
        return redirect('/register')


def parent_add_child(request):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')
    parent = get_object_or_404(Parent, id=request.session['account_id'])

    if request.method == 'POST':
        username = normalize_child_username(request.POST.get('username'))
        if not username:
            messages.error(request, 'Please enter a username using letters only, without numbers or special characters.')
        elif Child.objects.filter(username=username).exists():
            messages.error(request, 'That username is already taken. Please choose another one.')
        else:
            date_of_birth_raw = (request.POST.get('date_of_birth') or '').strip()
            date_of_birth = parse_date(date_of_birth_raw) if date_of_birth_raw else None
            if date_of_birth_raw and not date_of_birth:
                messages.error(request, 'Please enter a valid date of birth.')
                return render(request, 'add_child.html', {'parent': parent})
            if date_of_birth and date_of_birth > timezone.localdate():
                messages.error(request, 'Date of birth cannot be in the future.')
                return render(request, 'add_child.html', {'parent': parent})

            legacy_age = request.POST.get('age')
            try:
                legacy_age = int(legacy_age) if legacy_age not in (None, '') else None
            except (TypeError, ValueError):
                messages.error(request, 'Please enter a valid age.')
                return render(request, 'add_child.html', {'parent': parent})

            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            child_name = f'{first_name} {last_name}'.strip() or request.POST.get('child_name', '').strip() or username
            class_code = request.POST.get('class_code', '').strip()
            teacher = teacher_class = None
            if class_code:
                teacher, teacher_class = resolve_class_code(class_code)
                if not teacher:
                    messages.error(request, 'That teacher class code was not found.')
                    return render(request, 'add_child.html', {'parent': parent})

            child = Child.objects.create(
                parent=parent,
                username=username,
                first_name=first_name,
                last_name=last_name,
                name=child_name,
                date_of_birth=date_of_birth,  # age is calculated from this automatically — see Child.save()
                age=legacy_age,
                grade=int(request.POST['grade']),
                school_name=request.POST.get('school_name', '').strip() or (teacher.school_name if teacher else ''),
                parent_email=parent.email,
                photo=request.FILES.get('photo'),
                password=make_password(request.POST['password']),
                teacher=teacher,
                teacher_class=teacher_class,
            )
            mark_grade_confirmed_at_registration(child)
            messages.success(request, 'Child profile added.')
            return redirect('/parent/dashboard')

    return render(request, 'add_child.html', {'parent': parent})


# ───────────────────────── AI story generation ─────────────────────────
#
# A learner unlocks a fresh, personalised story once they've mastered every
# workbook lesson for their grade (95%+) — see AI_STORY_PASS_THRESHOLD and
# check_ai_story_eligibility below. Generation itself runs in a background
# thread (see run_ai_story_job/start_ai_story_job) so the request that kicks
# it off returns immediately; the frontend polls ai_story_job_status instead
# of blocking on a single slow request. maybe_start_ai_story_job is also
# called right after a learner finishes a lesson at pass-threshold or above,
# so a new story is often already waiting by the time they go looking for it.

AI_STORY_PASS_THRESHOLD = 95


def lesson_passed(child, lesson):
    """A lesson only counts as 'mastered' at 95%+, so comprehension has genuinely happened."""
    record = Progress.objects.filter(child=child, lesson=lesson).first()
    return bool(record and record.percentage >= AI_STORY_PASS_THRESHOLD)


class GeminiStoryGenerationError(Exception):
    """A learner-safe error raised when Gemini/Pollinations cannot create a story."""


def generate_gemini_story(grade, recent_titles):
    """Ask Gemini for a structured, CAPS-aligned practice story for one grade."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise GeminiStoryGenerationError('AI stories are not configured yet. Ask an adult to add the GEMINI_API_KEY setting.')
    theme = random.choice([
        'a school library discovery', 'a soccer practice', 'a family cooking day',
        'a visit to a science centre', 'a beach clean-up', 'a neighbourhood music day',
        'a bus trip to a museum', 'a lost-and-found kindness story', 'a rainy-day invention',
        'a young reader helping at a community event',
    ])
    word_count = '25-45' if grade == 1 else ('30-55' if grade == 2 else ('35-65' if grade == 3 else '70-100'))
    prompt = f'''Create one original English Home Language reading-practice story for a South African Grade {grade} learner.
Use this fresh theme: {theme}.
Avoid these recently used story titles and topics: {', '.join(recent_titles[-10:]) or 'none'}.
Return ONLY valid JSON with this exact shape:
{{"title":"short story title","character_description":"","pages":[{{"text":"","highlighted_words":["word"],"illustration_prompt":""}}],"questions":[{{"question":"","options":["","","",""],"answer":""}}],"visual_words":["","",""],"spelling":{{"display_text":"word with one missing vowel","answer":"complete word"}}}}
Rules: exactly 2 pages; each page has {word_count} age-appropriate words; each illustration_prompt describes that page only; use an everyday South African setting; age-appropriate vocabulary; no unsafe, frightening, commercial, or copyrighted characters; 3 comprehension questions; exactly 4 options per question; the answer must exactly match one option; and all content must be CAPS-aligned Grade {grade} reading practice. visual_words must contain exactly three different, single-word, concrete nouns from the story (for example "train", "book", "apple") that can be shown alone in a picture. Never use actions, people, places, descriptions, or compound words there.
character_description must be one concrete sentence describing the main character's appearance only — approximate age, hairstyle, one clothing colour/item, and skin tone — written so it can be pasted unchanged into an image-generation prompt every time that character appears, keeping them visually identical across illustrations.'''
    model = settings.GEMINI_MODEL
    payload = json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.7}}).encode('utf-8')
    api_request = UrlRequest(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', data=payload, headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key}, method='POST')
    try:
        with urlopen(api_request, timeout=45) as response:
            result = json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode('utf-8')).get('error', {})
            provider_message = detail.get('message', '')
        except (UnicodeDecodeError, json.JSONDecodeError):
            provider_message = ''
        if error.code in (401, 403):
            message = 'Gemini rejected the API key. Check that the key is active in Google AI Studio and restart SGILA.'
        elif error.code == 404:
            message = f'Gemini model "{model}" is not available for this API key. Check GEMINI_MODEL in .env.'
        elif error.code == 429:
            message = 'Gemini has reached its request limit. Wait a moment, then try again.'
        elif error.code == 400:
            message = 'Gemini could not accept the story request. Check the selected Gemini model and try again.'
        else:
            message = f'Gemini returned an error ({error.code}). Please try again later.'
        if provider_message:
            message = f'{message} Details: {provider_message[:180]}'
        raise GeminiStoryGenerationError(message) from error
    except URLError as error:
        raise GeminiStoryGenerationError('SGILA could not reach Gemini. Check the internet connection and try again.') from error
    try:
        text = ''.join(part.get('text', '') for part in result['candidates'][0]['content']['parts'])
        story = json.loads(text)
        visual_words = story.get('visual_words', [])
        if len(story['pages']) != 2 or len(story['questions']) != 3 or len(visual_words) != 3:
            raise ValueError('Unexpected story shape')
        if not str(story.get('character_description', '')).strip():
            raise ValueError('Missing character_description')
        for question in story['questions']:
            if len(question['options']) != 4 or question['answer'] not in question['options']:
                raise ValueError('Invalid question options')
        if any(not re.fullmatch(r'[A-Za-z]+', str(word).strip()) for word in visual_words):
            raise ValueError('Invalid visual word')
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise GeminiStoryGenerationError('Gemini returned a story in an unexpected format. Please try again.') from error
    return story


# Fixed art-direction brief reused for every image across the whole app. Combined with a
# locked seed and the story's own character_description, this is what keeps the images in
# one story looking like they belong together, since Pollinations has no image-input/reference
# mode — text (seed + wording) is the only consistency lever.
STORY_STYLE_BRIEF = (
    "children's picture-book illustration, soft warm gouache-and-watercolour style, rounded "
    "friendly shapes, bright gentle colour palette, everyday South African setting, "
    "no text, no letters, no logos, no watermarks"
)


def _build_pollinations_url(prompt_text, seed, width=1024, height=1024):
    encoded_prompt = urllib.parse.quote(prompt_text[:1500])
    url = (
        f'https://image.pollinations.ai/prompt/{encoded_prompt}'
        f'?width={width}&height={height}&seed={seed}&model={settings.POLLINATIONS_MODEL}&nologo=true'
    )
    if settings.POLLINATIONS_API_KEY:
        url += f'&token={settings.POLLINATIONS_API_KEY}'
    return url


def _save_image_bytes(image_bytes, content_type):
    suffix = '.png' if 'png' in content_type else '.jpg'
    folder = Path(settings.MEDIA_ROOT) / 'generated_stories'
    folder.mkdir(parents=True, exist_ok=True)
    filename = f'{uuid4().hex}{suffix}'
    (folder / filename).write_bytes(image_bytes)
    return f'{settings.MEDIA_URL}generated_stories/{filename}'


def _fetch_pollinations_image(url, max_attempts=3):
    """GET an image from Pollinations with retry/backoff.

    Pollinations' own docs flag 429 (rate limited) and 503 (overloaded) as expected,
    recoverable states, and 502 as usually-transient upstream trouble — so these are
    worth a short retry rather than failing the whole story generation immediately.
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        image_request = UrlRequest(url, headers={'User-Agent': 'SGILA-App/1.0'}, method='GET')
        try:
            with urlopen(image_request, timeout=60) as response:
                return response.read(), response.headers.get('Content-Type', '')
        except HTTPError as error:
            last_error = error
            if error.code in (429, 502, 503) and attempt < max_attempts:
                retry_after = error.headers.get('Retry-After') if error.headers else None
                try:
                    wait_seconds = float(retry_after) if retry_after else attempt * 2
                except ValueError:
                    wait_seconds = attempt * 2
                time.sleep(min(wait_seconds, 10))
                continue
            break
        except URLError as error:
            last_error = error
            if attempt < max_attempts:
                time.sleep(attempt * 2)
                continue
            break
    raise GeminiStoryGenerationError(
        'Could not create the story illustrations right now (Pollinations is busy). Please try again shortly.'
    ) from last_error


def generate_illustration(prompt, character_description, seed):
    """Generate and store one safe, story-specific illustration via Pollinations (free, unlimited).

    character_description and seed are shared across every image in one story — that pairing,
    not the model choice, is what makes the images look consistent instead of unrelated.
    """
    image_prompt = (
        f'{STORY_STYLE_BRIEF}. If the main character appears in this scene, draw them exactly '
        f'as: {character_description[:300]}. Scene to show: {str(prompt)[:600]}'
    )
    url = _build_pollinations_url(image_prompt, seed)
    image_bytes, content_type = _fetch_pollinations_image(url)
    return _save_image_bytes(image_bytes, content_type)


def generate_vocab_image(word, seed):
    """Generate one unmistakable object image for a visual-identification activity."""
    prompt = (
        f"{STORY_STYLE_BRIEF}. A single large, complete {word} centred in the frame. "
        "Show only that one object on a plain, softly coloured background. No people, animals, "
        "extra objects, scenery, labels, letters, numbers, logos, cropped object, or collage. "
        "The object must be immediately recognisable to a young learner."
    )
    url = _build_pollinations_url(prompt, seed)
    image_bytes, content_type = _fetch_pollinations_image(url)
    return _save_image_bytes(image_bytes, content_type)


def create_ai_story_for_grade(child):
    """Create a fresh Gemini-generated practice story after workbook completion.

    This is the actual generation work — it's slow (one Gemini call plus up to
    five sequential image calls) and is meant to be run from a background
    thread (see run_ai_story_job), never directly inside a request/response cycle.
    """
    recent_titles = list(Lesson.objects.filter(grade=child.grade, is_ai_generated=True).values_list('title', flat=True))
    story = generate_gemini_story(child.grade, recent_titles)
    character_description = story['character_description'].strip()
    seed = random.randint(1, 999999)

    illustrations = [
        generate_illustration(page.get('illustration_prompt', page['text']), character_description, seed)
        for page in story['pages']
    ]

    cover_image_url = illustrations[0]
    lesson = Lesson.objects.create(
        title=story['title'][:200],
        grade=child.grade,
        thumbnail_image=cover_image_url,
        curriculum_source='AI story collection — CAPS aligned',
        source_attribution=(
            'AI-generated practice story. Google Gemini writes the story and activities '
            f'to follow the Grade {child.grade} CAPS reading format; illustrations are AI-generated to match.'
        ),
        is_ai_generated=True,
        generated_for=child,
    )
    for page_number, page in enumerate(story['pages'], start=1):
        StoryPage.objects.create(
            lesson=lesson, page_number=page_number, text=page['text'],
            image_url=illustrations[page_number - 1],
            audio_url=f'voiceover:ai-story-{lesson.id}-page-{page_number}',
            highlighted_words=','.join(str(word) for word in page.get('highlighted_words', [])),
        )

    for item in story['questions']:
        options = list(item['options'])
        random.shuffle(options)
        ComprehensionQuestion.objects.create(
            lesson=lesson, question=item['question'], option_1=options[0], option_2=options[1],
            option_3=options[2], option_4=options[3], correct_answer=item['answer'],
        )

    story_text = " ".join([page.get('text', '') for page in story['pages']])
    # Grab words longer than 3 letters to use as trick options
    story_words = list(set([w.strip('.,!?()"\'').title() for w in story_text.split() if len(w.strip('.,!?()"\'')) > 3]))
    fallback_pool = ['Farm', 'School', 'Book', 'Tree', 'House', 'Car', 'Dog', 'Cat', 'Sun', 'Bird']
    distractor_pool = list(set(story_words + fallback_pool))

    for word_index, word in enumerate(story['visual_words']):
        word = str(word).strip().title()[:100]
        vocab_image_url = generate_vocab_image(word, seed + word_index + 1)
        safe_pool = [w for w in distractor_pool if w.lower() != word.lower()]
        wrong_options = random.sample(safe_pool, min(3, len(safe_pool)))
        options = [word] + wrong_options
        random.shuffle(options)
        word_options_str = ','.join(options)
        VisualActivityItem.objects.create(lesson=lesson, correct_word=word, word_options=word_options_str, image_url=vocab_image_url)
        PronunciationWord.objects.create(lesson=lesson, word=word, english_audio=f'voiceover:ai-story-{word.lower()}')

    spelling = story['spelling']
    SpellingActivity.objects.create(
        lesson=lesson, activity_type=SpellingActivity.FILL_VOWEL,
        display_text=spelling['display_text'][:200], answer=spelling['answer'][:200],
    )
    return lesson


def run_ai_story_job(job_id):
    """Background-thread entry point: does the slow work, then records the outcome on the job row.

    Coordination is entirely through the AIStoryJob row in the database — nothing is kept
    in memory that the polling requests need — so this is safe even if the web server runs
    multiple worker processes.
    """
    try:
        job = AIStoryJob.objects.get(id=job_id)
    except AIStoryJob.DoesNotExist:
        return
    job.status = AIStoryJob.STATUS_RUNNING
    job.save(update_fields=['status', 'updated_at'])
    try:
        lesson = create_ai_story_for_grade(job.child)
    except GeminiStoryGenerationError as error:
        job.status = AIStoryJob.STATUS_ERROR
        job.error_message = str(error)
        job.save(update_fields=['status', 'error_message', 'updated_at'])
    except Exception:  # noqa: BLE001 — a background thread must never crash silently
        job.status = AIStoryJob.STATUS_ERROR
        job.error_message = 'Something went wrong creating the story. Please try again.'
        job.save(update_fields=['status', 'error_message', 'updated_at'])
    else:
        job.lesson = lesson
        job.status = AIStoryJob.STATUS_DONE
        job.save(update_fields=['lesson', 'status', 'updated_at'])


def start_ai_story_job(child, grade):
    """Create (or reuse) a pending/running AI story job and kick off its background thread."""
    existing = AIStoryJob.objects.filter(
        child=child, grade=grade, status__in=[AIStoryJob.STATUS_PENDING, AIStoryJob.STATUS_RUNNING],
    ).order_by('-created_at').first()
    if existing:
        return existing
    job = AIStoryJob.objects.create(child=child, grade=grade, status=AIStoryJob.STATUS_PENDING)
    threading.Thread(target=run_ai_story_job, args=(job.id,), daemon=True).start()
    return job


def check_ai_story_eligibility(child, grade):
    """Shared gate used by both the manual 'explore more stories' button and the
    automatic post-lesson trigger.

    Returns (eligible, error_message, redirect_hint) where redirect_hint is only set
    when the learner should be sent somewhere specific (e.g. back to an unfinished story).
    """
    if grade not in (1, 2, 3, 4):
        return False, 'AI practice stories are available for Grades 1 to 4.', f'/grade/{grade}'

    all_lessons = Lesson.objects.filter(grade=grade)
    required_lessons = list(all_lessons.filter(is_ai_generated=False)) + list(all_lessons.filter(
        is_ai_generated=True, generated_for__isnull=True, curriculum_source='AI story collection — CAPS aligned',
    ))
    if not required_lessons or not all(lesson_passed(child, lesson) for lesson in required_lessons):
        return (
            False,
            f'Score at least {AI_STORY_PASS_THRESHOLD}% on every workbook story before creating an AI story.',
            f'/grade/{grade}',
        )

    current_ai_lesson = Lesson.objects.filter(
        grade=grade, is_ai_generated=True, generated_for=child,
    ).order_by('-created_at').first()
    if current_ai_lesson and not lesson_passed(child, current_ai_lesson):
        return (
            False,
            f'Finish your current story with at least {AI_STORY_PASS_THRESHOLD}% before unlocking a new one.',
            f'/lessons/{current_ai_lesson.id}/story',
        )

    return True, None, None


def maybe_start_ai_story_job(child, grade):
    """Called right after a learner finishes a lesson at pass-threshold or above.

    Silently starts generating their next AI story in the background — no button click
    required — so it's often ready by the time they go looking for it. Safe to call on
    every results-page render: check_ai_story_eligibility and start_ai_story_job both
    no-op if a story isn't actually due yet or a job is already in flight.
    """
    if not settings.GEMINI_API_KEY:
        return
    try:
        eligible, _, _ = check_ai_story_eligibility(child, grade)
        if eligible:
            start_ai_story_job(child, grade)
    except Exception:  # noqa: BLE001 — this is a background nicety, never worth breaking results page over
        pass


@require_http_methods(['POST'])
def generate_ai_story_ajax(request, grade):
    """JSON endpoint for the 'Explore more stories' button.

    Starts (or reuses) a background job and returns immediately — it never blocks on
    Gemini/Pollinations itself. The frontend polls ai_story_job_status for progress.
    """
    child, response = learner_required(request)
    if response:
        return JsonResponse({'success': False, 'error': 'Please sign in as a learner first.'}, status=401)
    if child.grade != grade:
        return JsonResponse({'success': False, 'error': 'This story set belongs to a different grade.'}, status=403)

    eligible, error_message, redirect_hint = check_ai_story_eligibility(child, grade)
    if not eligible:
        return JsonResponse({'success': False, 'error': error_message, 'redirect_url': redirect_hint}, status=400)

    if not settings.GEMINI_API_KEY:
        return JsonResponse({
            'success': False,
            'error': 'AI stories are not configured yet. Ask an adult to add the GEMINI_API_KEY setting.',
        }, status=503)

    job = start_ai_story_job(child, grade)
    return JsonResponse({'success': True, 'job_id': job.id, 'status': job.status})


@require_http_methods(['GET'])
def ai_story_job_status(request, job_id):
    """Polled by the frontend every couple seconds while a story is being created."""
    child, response = learner_required(request)
    if response:
        return JsonResponse({'success': False, 'error': 'Please sign in as a learner first.'}, status=401)
    job = get_object_or_404(AIStoryJob, id=job_id)
    if job.child_id != child.id:
        raise Http404('Job not found.')

    data = {'success': True, 'status': job.status}
    if job.status == AIStoryJob.STATUS_DONE and job.lesson_id:
        data.update({
            'lesson_id': job.lesson_id,
            'title': job.lesson.title,
            'thumbnail_image': job.lesson.thumbnail_image,
            'redirect_url': f'/lessons/{job.lesson_id}/story',
        })
    elif job.status == AIStoryJob.STATUS_ERROR:
        data['error'] = job.error_message or 'Could not create a story right now. Please try again.'
    return JsonResponse(data)


def grade3_activities_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=3)
    return render(request, 'grade3_activities.html', {
        'lesson': lesson,
        'child': child,
    })


@require_http_methods(['POST'])
def complete_grade3_activities(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=3)
    try:
        scores = json.loads(request.body or '{}')
        total_score = int(scores.get('total_score', 0))
        total_possible = int(scores.get('total_possible', 24))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid activity score.'}, status=400)
    Progress.objects.update_or_create(
        child=child,
        lesson=lesson,
        defaults={
            'comprehension_score': int(scores.get('comprehension_score', 0)),
            'visual_score': int(scores.get('visual_score', 0)),
            'spelling_score': int(scores.get('spelling_score', 0)),
            'total_score': total_score,
            'total_possible': total_possible,
            'stars_earned': (
                3 if total_score / max(total_possible, 1) >= .9
                else 2 if total_score / max(total_possible, 1) >= .7
                else 1
            ),
            'assessment_scores': {
                'grade3_activities': {
                    'score': total_score,
                    'total': total_possible,
                },
            },
        },
    )
    return JsonResponse({'completed': True})


def grade_home(request, grade):
    child, response = learner_required(request)
    if response:
        return response
    if child.grade != grade:
        return redirect_after_forbidden(request)

    if request.method == 'POST':
        class_code = request.POST.get('class_code', '').strip()
        if not class_code:
            messages.error(request, 'Please enter a class code to link your profile.')
            return redirect(f'/grade/{grade}')

        if child.teacher_class:
            messages.info(request, 'Your learner profile is already linked to a class.')
            return redirect(f'/grade/{grade}')

        if not link_child_to_class(child, class_code):
            messages.error(request, 'That teacher class code was not found.')
            return redirect(f'/grade/{grade}')

        child.save(update_fields=['teacher', 'teacher_class', 'school_name'])
        messages.success(request, 'Class code linked successfully. You can now continue your lessons.')
        return redirect(f'/grade/{grade}')

    all_lessons = Lesson.objects.filter(grade=grade).order_by('id')
    curated_lessons = list(all_lessons.filter(is_ai_generated=False))
    # Reviewed/shared AI stories are visible to the whole grade. A story generated
    # for one specific learner is private to them (see story_page's ownership check).
    public_ai_stories = list(all_lessons.filter(
        is_ai_generated=True,
        generated_for__isnull=True,
        curriculum_source='AI story collection — CAPS aligned',
    ).order_by('id'))
    # Only the most recent personal AI story is ever shown — once a new one is
    # generated, the previous one quietly drops off this list (it's kept in the
    # database for progress history, just not shown as a lesson card any more).
    latest_ai_lesson = all_lessons.filter(
        is_ai_generated=True, generated_for=child,
    ).order_by('-created_at').first()
    lessons = curated_lessons + public_ai_stories + ([latest_ai_lesson] if latest_ai_lesson else [])

    records = Progress.objects.filter(child=child)
    progress_by_lesson = {record.lesson_id: record for record in records}
    lesson_data = []
    for lesson in lessons:
        record = progress_by_lesson.get(lesson.id)
        group_sizes = {}
        for group_number in lesson.reading_activities.values_list('group_number', flat=True):
            if group_number:
                group_sizes[group_number] = group_sizes.get(group_number, 0) + 1
        questions_per_activity = (
            next(iter(group_sizes.values()))
            if group_sizes and len(set(group_sizes.values())) == 1
            else None
        )
        lesson_data.append({
            'id': lesson.id,
            'title': lesson.title,
            'grade': lesson.grade,
            'thumbnail_image': lesson.thumbnail_image,
            'completed': bool(record),
            'stars': range(record.stars_earned) if record else range(0),
            'is_current_ai_story': lesson.is_ai_generated and lesson.id == getattr(latest_ai_lesson, 'id', None),
            'activities': activity_choices_for(lesson),
            'resume_url': (child.paused_activities or {}).get(str(lesson.id)),
            'activity_count': len(group_sizes),
            'questions_per_activity': questions_per_activity,
        })

    required_lessons = curated_lessons + public_ai_stories
    workbook_complete = bool(required_lessons) and all(
        lesson_passed(child, lesson) for lesson in required_lessons
    )
    # The "explore more stories" offer only opens once the workbook is mastered AND,
    # if a personal AI story already exists, once that one is mastered too.
    ai_story_available = workbook_complete and (
        latest_ai_lesson is None or lesson_passed(child, latest_ai_lesson)
    )
    active_ai_job = AIStoryJob.objects.filter(
        child=child, grade=grade, status__in=[AIStoryJob.STATUS_PENDING, AIStoryJob.STATUS_RUNNING],
    ).order_by('-created_at').first()

    return render(request, 'grade_home.html', {
        'lessons': lesson_data,
        'grade': grade,
        'child': child,
        'child_name': child.name,
        'completed_count': records.count(),
        'total_stars': sum(r.stars_earned for r in records),
        'ai_story_available': ai_story_available,
        'ai_story_job_id': active_ai_job.id if active_ai_job else None,
        'grades_with_ai': (1, 2, 3, 4),
    })


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def activity_pause(request, lesson_id):
    """Provide the running score and save a safe resume destination for a learner."""
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)

    if request.method == 'POST':
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            data = {}
        resume_url = data.get('resume_url', '')
        parsed_resume_url = urllib.parse.urlsplit(resume_url)
        allowed_urls = {item['url'] for item in activity_choices_for(lesson)}
        if parsed_resume_url.path not in allowed_urls or parsed_resume_url.fragment:
            return JsonResponse({'error': 'Invalid activity to resume.'}, status=400)
        if parsed_resume_url.path.endswith('/questions'):
            query = urllib.parse.parse_qs(parsed_resume_url.query)
            indexes = query.get('activity_index', [])
            activity_index = int(indexes[0]) if len(indexes) == 1 and indexes[0].isdigit() else -1
            activity_total = lesson.reading_activities.count() or lesson.questions.count()
            if activity_index < 0 or activity_index >= activity_total:
                return JsonResponse({'error': 'Invalid activity to resume.'}, status=400)
            resume_url = f'{parsed_resume_url.path}?activity_index={activity_index}'
        elif parsed_resume_url.query:
            return JsonResponse({'error': 'Invalid activity to resume.'}, status=400)
        paused_activities = dict(child.paused_activities or {})
        paused_activities[str(lesson.id)] = resume_url
        child.paused_activities = paused_activities
        child.save(update_fields=['paused_activities'])
        request.session[f'lesson_{lesson.id}_resume_url'] = resume_url
        request.session.modified = True

    score, possible = activity_score_summary(request, lesson)
    return JsonResponse({'score': score, 'total': possible})


def story_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    if lesson.is_ai_generated and lesson.generated_for_id and lesson.generated_for_id != child.id:
        raise Http404('This generated story belongs to another learner.')
    pages = [{
        'page_number': p.page_number,
        'text': p.text,
        'image_url': p.image_url,
        'audio_url': p.audio_url,
        'highlighted_words': p.get_highlighted_words(),
    } for p in lesson.pages.all()]
    if lesson.grade == 3:
        first_activity_url = f'/lessons/{lesson_id}/activities'
    else:
        first_activity_url = f'/lessons/{lesson_id}/questions'
    return render(request, 'story.html', {
        'lesson': lesson,
        'pages': pages,
        'child': child,
        'activity_resume_url': activity_resume_url(request, child, lesson),
        'first_activity_url': first_activity_url,
    })


@never_cache
def questions_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    if lesson.grade == 3:
        return redirect(f'/lessons/{lesson_id}/activities')
    total_questions = lesson.reading_activities.count() or ComprehensionQuestion.objects.filter(lesson=lesson).count()
    if lesson.reading_activities.filter(skill='spelling').exists():
        next_activity_url = f'/lessons/{lesson_id}/results'
    elif lesson.visual_items.exists():
        next_activity_url = f'/lessons/{lesson_id}/visual-activity'
    elif lesson.pronunciation_words.exists():
        next_activity_url = f'/lessons/{lesson_id}/pronunciation'
    elif lesson.spelling_activities.exists():
        next_activity_url = f'/lessons/{lesson_id}/spelling'
    else:
        next_activity_url = f'/lessons/{lesson_id}/results'
    return render(request, 'questions.html', {
        'lesson': lesson,
        'lesson_id': lesson_id,
        'child': child,
        'child_id': child.id,
        'total_questions': total_questions,
        'next_activity_url': next_activity_url,
    })


def visual_activity_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    if lesson.grade == 3 and not lesson.visual_items.exists():
        if lesson.pronunciation_words.exists():
            return redirect(f'/lessons/{lesson_id}/pronunciation')
        if lesson.spelling_activities.exists():
            return redirect(f'/lessons/{lesson_id}/spelling')
        return redirect(f'/lessons/{lesson_id}/results')
    return render(request, 'visual_activity.html', {
        'lesson': lesson,
        'child': child,
        'items': lesson.visual_items.all(),
    })


def pronunciation_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    return render(request, 'pronunciation.html', {
        'lesson': lesson,
        'words': lesson.pronunciation_words.all(),
    })


def normalise_spelling_answer(value, loose=False):
    value = re.sub(r'\s+', ' ', (value or '').strip().lower())
    if loose:
        value = re.sub(r'[^\w\s]', '', value)
        value = re.sub(r'\s+', ' ', value).strip()
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


@require_http_methods(["GET", "POST"])
def spelling_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    activities = list(lesson.spelling_activities.all())

    if request.method == 'POST':
        spelling_score = 0
        for activity in activities:
            answer = request.POST.get(f'activity_{activity.id}', '').strip()
            if spelling_answer_is_correct(activity, answer):
                spelling_score += 1

        request.session[f'lesson_{lesson_id}_spelling_score'] = spelling_score
        request.session[f'lesson_{lesson_id}_spelling_total'] = len(activities)
        return redirect(f'/lessons/{lesson_id}/results')

    return render(request, 'spelling.html', {'lesson': lesson, 'activities': activities, 'child': child})


def add_assessment_score(scores, key, score, total):
    try:
        score = max(int(score), 0)
        total = max(int(total), 0)
    except (TypeError, ValueError):
        return
    if not total:
        return
    bucket = scores.setdefault(key, {'score': 0, 'total': 0})
    bucket['score'] += min(score, total)
    bucket['total'] += total


def session_assessment_scores(request, lesson):
    prefix = f'lesson_{lesson.id}'
    scores = {}
    reading_scores = request.session.get(f'{prefix}_reading_skill_scores', {})
    if isinstance(reading_scores, dict):
        for key, values in reading_scores.items():
            if isinstance(values, dict):
                add_assessment_score(scores, key, values.get('score'), values.get('total'))

    if not reading_scores:
        add_assessment_score(
            scores,
            'reading',
            request.session.get(f'{prefix}_comprehension_score', 0),
            request.session.get(
                f'{prefix}_comprehension_total',
                lesson.reading_activities.count() or lesson.questions.count(),
            ),
        )

    add_assessment_score(
        scores,
        'visual_literacy',
        request.session.get(f'{prefix}_visual_score', 0),
        request.session.get(f'{prefix}_visual_total', 0),
    )
    add_assessment_score(
        scores,
        'spelling',
        request.session.get(f'{prefix}_spelling_score', 0),
        request.session.get(f'{prefix}_spelling_total', 0),
    )

    legacy_scores = [
        ('sequencing', 'seq_score', 'seq_total', lesson.sequencing_activities.exists()),
        ('inference', 'inference_score', 'inference_total', lesson.inference_questions.exists()),
        ('emotional_literacy', 'feelings_score', 'feelings_total', lesson.feelings_questions.exists()),
        ('cause_effect', 'ce_score', 'ce_total', lesson.cause_effect_pairs.exists()),
        ('summarising', 'theme_score', 'theme_total', lesson.theme_questions.exists()),
        ('prediction', 'prediction_score', 'prediction_total', lesson.prediction_questions.exists()),
    ]
    for key, score_suffix, total_suffix, has_activity in legacy_scores:
        if has_activity and f'{prefix}_{total_suffix}' in request.session:
            add_assessment_score(
                scores,
                key,
                request.session.get(f'{prefix}_{score_suffix}', 0),
                request.session.get(f'{prefix}_{total_suffix}', 0),
            )
    return scores


def results_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    prefix = f'lesson_{lesson_id}'
    # A completed lesson no longer needs its "continue later" marker.
    paused_activities = dict(child.paused_activities or {})
    paused_activities.pop(str(lesson_id), None)
    child.paused_activities = paused_activities
    child.save(update_fields=['paused_activities'])
    request.session.pop(f'{prefix}_resume_url', None)

    fresh_suffixes = (
        'reading_skill_scores', 'comprehension_score', 'comprehension_total',
        'visual_score', 'visual_total', 'spelling_score', 'spelling_total',
        'seq_score', 'seq_total', 'inference_score', 'inference_total',
        'feelings_score', 'feelings_total', 'ce_score', 'ce_total',
        'theme_score', 'theme_total', 'prediction_score', 'prediction_total',
    )
    has_fresh_result = any(f'{prefix}_{suffix}' in request.session for suffix in fresh_suffixes)

    if has_fresh_result:
        assessment_scores = session_assessment_scores(request, lesson)
        total_score = sum(item['score'] for item in assessment_scores.values())
        total_possible = sum(item['total'] for item in assessment_scores.values())
        percentage = round((total_score / total_possible) * 100) if total_possible else 0
        stars = 3 if percentage >= 90 else (2 if percentage >= 70 else 1)

        reading_keys = set(assessment_scores) - {'visual_literacy', 'spelling'}
        comprehension_score = sum(assessment_scores[key]['score'] for key in reading_keys)
        visual_score = assessment_scores.get('visual_literacy', {}).get('score', 0)
        spelling_score = assessment_scores.get('spelling', {}).get('score', 0)
        record, _ = Progress.objects.update_or_create(
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

        for session_key in list(request.session.keys()):
            if session_key.startswith(f'{prefix}_'):
                request.session.pop(session_key, None)
        request.session.modified = True
    else:
        record = Progress.objects.filter(child=child, lesson=lesson).first()
        if not record:
            messages.error(request, 'Complete the lesson before viewing results.')
            return redirect(f'/grade/{child.grade}')
        breakdown = rows_for_record(record)
        total_score = sum(item['score'] for item in breakdown)
        total_possible = sum(item['total'] for item in breakdown)
        percentage = round((total_score / total_possible) * 100) if total_possible else 0
        stars = record.stars_earned

    if has_fresh_result:
        breakdown = rows_for_record(record)
    ranked = sorted(breakdown, key=lambda item: (-item['pct'], item['label']))
    focus_ranked = sorted(breakdown, key=lambda item: (item['pct'], item['label']))
    best_activities = [item for item in ranked if item['pct'] > 0][:2]
    best_keys = {item['key'] for item in best_activities}
    worst_activities = [
        item for item in focus_ranked
        if item['pct'] < 100 and item['key'] not in best_keys
    ][:2]
    reaction = 'Amazing work' if percentage >= 90 else ('Great job' if percentage >= 70 else 'Good effort')
    context = {
        'child': child,
        'lesson': lesson,
        'total_score': total_score,
        'total_possible': total_possible,
        'percentage': percentage,
        'stars': range(stars),
        'reaction': reaction,
        'breakdown': breakdown,
        'best_activities': best_activities,
        'worst_activities': worst_activities,
    }
    return render(request, 'results_grade4.html' if lesson.grade == 4 else 'results.html', context)


def legacy_results_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    prefix = f'lesson_{lesson_id}'

    # ── Grade 4 results path ──────────────────────────────────────────────────
    if lesson.grade == 4:
        # Keys written by each Grade-4 activity check endpoint
        grade4_keys = [
            'comprehension_score', 'comprehension_total',   # Activity 1
            'seq_score',           'seq_total',              # Activity 2
            'inference_score',     'inference_total',        # Activity 3
            'feelings_score',      'feelings_total',         # Activity 4
            'ce_score',            'ce_total',               # Activity 5
            'theme_score',         'theme_total',            # Activity 6
        ]
        has_fresh = any(f'{prefix}_{k}' in request.session for k in grade4_keys)

        if not has_fresh:
            # Show results from the stored Grade4ActivityProgress record
            g4rec = Grade4ActivityProgress.objects.filter(child=child, lesson=lesson).first()
            if not g4rec:
                messages.error(request, 'Complete the lesson before viewing results.')
                return redirect(f'/grade/{child.grade}')
            percentage = g4rec.percentage
            reaction = 'Amazing work' if percentage >= 90 else ('Great job' if percentage >= 70 else 'Good effort')
            all_scores = g4rec.activity_scores()
            return render(request, 'results_grade4.html', {
                'child': child, 'lesson': lesson,
                'total_score': g4rec.total_score,
                'total_possible': g4rec.total_possible,
                'percentage': percentage,
                'stars': range(g4rec.stars_earned),
                'reaction': reaction,
                'breakdown': [
                    {'label': a['label'], 'score': a['score'], 'total': a['total']}
                    for a in all_scores
                ],
                'best_activities': all_scores[:2],
                'worst_activities': all_scores[-2:],
            })

        def gs(key, fallback=0):
            return int(request.session.get(f'{prefix}_{key}', fallback))

        # Activity 1 — Comprehension Questions (seeded via ComprehensionQuestion)
        comp_score  = gs('comprehension_score');  comp_total  = gs('comprehension_total',  lesson.questions.count())
        # Activity 2 — Sequencing
        seq_score   = gs('seq_score');            seq_total   = gs('seq_total',   lesson.sequencing_activities.count())
        # Activity 3 — Inference
        inf_score   = gs('inference_score');      inf_total   = gs('inference_total',   lesson.inference_questions.count())
        # Activity 4 — Feelings
        feel_score  = gs('feelings_score');       feel_total  = gs('feelings_total',  lesson.feelings_questions.count())
        # Activity 5 — Cause & Effect
        ce_score    = gs('ce_score');             ce_total    = gs('ce_total',    lesson.cause_effect_pairs.count())
        # Activity 6 — Theme / Main Lesson
        theme_score = gs('theme_score');          theme_total = gs('theme_total', lesson.theme_questions.count())

        total_score    = comp_score + seq_score + inf_score + feel_score + ce_score + theme_score
        total_possible = comp_total + seq_total + inf_total + feel_total + ce_total + theme_total
        percentage = round((total_score / total_possible) * 100) if total_possible else 0

        stars    = 3 if percentage >= 90 else (2 if percentage >= 70 else 1)
        reaction = 'Amazing work' if percentage >= 90 else ('Great job' if percentage >= 70 else 'Good effort')

        # Save detailed per-activity record
        g4rec, _ = Grade4ActivityProgress.objects.update_or_create(
            child=child,
            lesson=lesson,
            defaults={
                'comprehension_score': comp_score,  'comprehension_total': comp_total,
                'sequencing_score':    seq_score,   'sequencing_total':    seq_total,
                'inference_score':     inf_score,   'inference_total':     inf_total,
                'feelings_score':      feel_score,  'feelings_total':      feel_total,
                'cause_effect_score':  ce_score,    'cause_effect_total':  ce_total,
                'theme_score':         theme_score, 'theme_total':         theme_total,
                'total_score':         total_score,
                'total_possible':      total_possible,
                'stars_earned':        stars,
            },
        )

        # Also keep the legacy Progress record so the existing dashboard still works
        Progress.objects.update_or_create(
            child=child, lesson=lesson,
            defaults={
                'comprehension_score': comp_score + inf_score + feel_score + theme_score,
                'visual_score':        ce_score,
                'spelling_score':      seq_score,
                'total_score':         total_score,
                'total_possible':      total_possible,
                'stars_earned':        stars,
            },
        )

        if percentage >= AI_STORY_PASS_THRESHOLD:
            maybe_start_ai_story_job(child, lesson.grade)

        breakdown = [
            {'label': 'Comprehension',  'score': comp_score,  'total': comp_total},
            {'label': 'Sequencing',     'score': seq_score,   'total': seq_total},
            {'label': 'Inference',      'score': inf_score,   'total': inf_total},
            {'label': 'Feelings',       'score': feel_score,  'total': feel_total},
            {'label': 'Cause & Effect', 'score': ce_score,    'total': ce_total},
            {'label': 'Main Lesson',    'score': theme_score, 'total': theme_total},
        ]
        breakdown = [item for item in breakdown if item['total'] > 0]
        all_scores = g4rec.activity_scores()

        # Clear session
        for k in grade4_keys:
            request.session.pop(f'{prefix}_{k}', None)
        for extra in ['question_answers', 'inference_answers', 'feelings_answers', 'ce_answers']:
            request.session.pop(f'{prefix}_{extra}', None)
        request.session.modified = True

        return render(request, 'results_grade4.html', {
            'child': child, 'lesson': lesson,
            'total_score': total_score,
            'total_possible': total_possible,
            'percentage': percentage,
            'stars': range(stars),
            'reaction': reaction,
            'breakdown': breakdown,
            'best_activities': all_scores[:2],
            'worst_activities': all_scores[-2:],
        })

    # ── Original results path (all other grades) ──────────────────────────────
    score_keys = [
        'comprehension_score', 'comprehension_total', 'visual_score',
        'visual_total', 'spelling_score', 'spelling_total',
    ]

    has_fresh_result = any(f'{prefix}_{key}' in request.session for key in score_keys)
    if not has_fresh_result:
        record = Progress.objects.filter(child=child, lesson=lesson).first()
        if not record:
            messages.error(request, 'Complete the lesson before viewing results.')
            return redirect(f'/grade/{child.grade}')

        percentage = record.percentage
        if percentage >= 90:
            reaction = 'Amazing work'
        elif percentage >= 70:
            reaction = 'Great job'
        else:
            reaction = 'Good effort'

        return render(request, 'results.html', {
            'child': child,
            'lesson': lesson,
            'comprehension_score': record.comprehension_score,
            'comprehension_total': lesson.questions.count(),
            'visual_score': record.visual_score,
            'visual_total': lesson.visual_items.count(),
            'spelling_score': record.spelling_score,
            'spelling_total': lesson.spelling_activities.count(),
            'total_score': record.total_score,
            'total_possible': record.total_possible,
            'percentage': percentage,
            'stars': range(record.stars_earned),
            'reaction': reaction,
        })

    comprehension_score = int(request.session.get(f'{prefix}_comprehension_score', 0))
    comprehension_total = int(request.session.get(f'{prefix}_comprehension_total', lesson.questions.count()))
    visual_score = int(request.session.get(f'{prefix}_visual_score', 0))
    visual_total = int(request.session.get(f'{prefix}_visual_total', lesson.visual_items.count()))
    spelling_score = int(request.session.get(f'{prefix}_spelling_score', 0))
    spelling_total = int(request.session.get(f'{prefix}_spelling_total', lesson.spelling_activities.count()))

    total_score = comprehension_score + visual_score + spelling_score
    total_possible = comprehension_total + visual_total + spelling_total
    percentage = round((total_score / total_possible) * 100) if total_possible else 0
    if percentage >= 90:
        stars = 3
        reaction = 'Amazing work'
    elif percentage >= 70:
        stars = 2
        reaction = 'Great job'
    else:
        stars = 1
        reaction = 'Good effort'

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
        },
    )

    if percentage >= AI_STORY_PASS_THRESHOLD:
        maybe_start_ai_story_job(child, lesson.grade)

    for suffix in score_keys:
        request.session.pop(f'{prefix}_{suffix}', None)
    request.session.pop(f'{prefix}_question_answers', None)
    request.session.pop(f'{prefix}_visual_answers', None)

    return render(request, 'results.html', {
        'child': child,
        'lesson': lesson,
        'comprehension_score': comprehension_score,
        'comprehension_total': comprehension_total,
        'visual_score': visual_score,
        'visual_total': visual_total,
        'spelling_score': spelling_score,
        'spelling_total': spelling_total,
        'total_score': total_score,
        'total_possible': total_possible,
        'percentage': percentage,
        'stars': range(stars),
        'reaction': reaction,
    })


def legacy_dashboard_page(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    if not user_can_view_child(request, child):
        messages.error(request, 'You do not have access to that learner report.')
        return redirect_after_forbidden(request)

    records = list(
        Progress.objects.filter(child=child)
        .select_related('lesson')
        .prefetch_related('lesson__questions', 'lesson__visual_items', 'lesson__spelling_activities')
        .order_by('-completed_on')
    )
    for record in records:
        record.stars_range = range(record.stars_earned)

    def activity_percentage(score, activity_items):
        total_items = len(activity_items)
        return round((score / total_items) * 100) if total_items else 0

    total_lessons = len(records)
    avg_score = round(sum(r.percentage for r in records) / total_lessons) if records else 0
    total_stars = sum(r.stars_earned for r in records)
    best_lesson = max(records, key=lambda r: r.percentage, default=None)

    # ── Grade 4: use per-activity scores from Grade4ActivityProgress ──────────
    is_grade4 = child.grade == 4
    g4_best2 = []
    g4_worst2 = []

    if is_grade4:
        g4_records = list(
            Grade4ActivityProgress.objects.filter(child=child)
            .select_related('lesson')
            .order_by('-completed_on')
        )
        if g4_records:
            # Aggregate average per activity across all completed lessons
            activity_labels = [
                ('Comprehension', 'comprehension_score', 'comprehension_total'),
                ('Sequencing',    'sequencing_score',    'sequencing_total'),
                ('Inference',     'inference_score',     'inference_total'),
                ('Feelings',      'feelings_score',      'feelings_total'),
                ('Cause & Effect','cause_effect_score',  'cause_effect_total'),
                ('Main Lesson',   'theme_score',         'theme_total'),
            ]
            avg_activities = []
            for label, s_field, t_field in activity_labels:
                total_s = sum(getattr(r, s_field) for r in g4_records)
                total_t = sum(getattr(r, t_field) for r in g4_records)
                pct = round((total_s / total_t) * 100) if total_t else 0
                avg_activities.append({'label': label, 'pct': pct, 'score': total_s, 'total': total_t})
            avg_activities.sort(key=lambda x: x['pct'], reverse=True)
            g4_best2 = avg_activities[:2]
            g4_worst2 = avg_activities[-2:]

            avg_comprehension = g4_best2[0]['pct'] if g4_best2 else 0
            avg_visual = g4_worst2[-1]['pct'] if g4_worst2 else 0
            avg_spelling = 0
        else:
            avg_comprehension = avg_visual = avg_spelling = 0
        needs_focus = ''
        needs_focus_tip = ''
        if g4_worst2:
            needs_focus = g4_worst2[-1]['label']
            needs_focus_tip = f"Practise {g4_worst2[-1]['label'].lower()} questions to improve your score."
    else:
        avg_comprehension = round(
            sum(activity_percentage(r.comprehension_score, r.lesson.questions.all()) for r in records) / total_lessons
        ) if records else 0
        avg_visual = round(
            sum(activity_percentage(r.visual_score, r.lesson.visual_items.all()) for r in records) / total_lessons
        ) if records else 0
        avg_spelling = round(
            sum(activity_percentage(r.spelling_score, r.lesson.spelling_activities.all()) for r in records) / total_lessons
        ) if records else 0

        needs_focus = ''
        needs_focus_tip = ''
        if records:
            if avg_score == 100:
                needs_focus = 'Good job! you got everything correct'
            else:
                focus_options = {
                    'Reading': (avg_comprehension, 'Comprehension and story questions'),
                    'Visual': (avg_visual, 'Picture matching activities'),
                    'Spelling': (avg_spelling, 'Copy writing and missing letters'),
                }
                needs_focus, (_, needs_focus_tip) = min(focus_options.items(), key=lambda item: item[1][0])

    return render(request, 'dashboard.html', {
        'child': child,
        'records': records,
        'total_lessons': total_lessons,
        'avg_score': avg_score,
        'total_stars': total_stars,
        'avg_comprehension': avg_comprehension,
        'avg_visual': avg_visual,
        'avg_spelling': avg_spelling,
        'best_lesson': best_lesson,
        'needs_focus': needs_focus,
        'needs_focus_tip': needs_focus_tip,
        'is_grade4': is_grade4,
        'g4_best2': g4_best2,
        'g4_worst2': g4_worst2,
    })


def legacy_build_dashboard_row(child):
    records = list(
        Progress.objects.filter(child=child)
        .select_related('lesson')
        .prefetch_related('lesson__questions', 'lesson__visual_items', 'lesson__spelling_activities')
        .order_by('-completed_on')
    )
    lessons_done = len(records)
    percentages = [record.percentage for record in records]
    average = round(sum(percentages) / len(percentages)) if percentages else 0
    total_lessons = Lesson.objects.filter(grade=child.grade).count() or Lesson.objects.count()
    progress_percent = round((lessons_done / total_lessons) * 100) if total_lessons else 0
    stars = sum(record.stars_earned for record in records)

    def activity_percentage(score, activity_items):
        total_items = len(activity_items)
        return round((score / total_items) * 100) if total_items else 0

    latest = records[0] if records else None
    best_lesson = max(records, key=lambda record: record.percentage, default=None)
    best_score = best_lesson.percentage if best_lesson else 0
    perfect_work = bool(records) and all(record.total_possible and record.total_score == record.total_possible for record in records)

    # ── Grade 4: aggregate per-activity averages from Grade4ActivityProgress ──
    is_grade4 = child.grade == 4
    g4_best2 = []
    g4_worst2 = []

    if is_grade4:
        g4_records = list(
            Grade4ActivityProgress.objects.filter(child=child).order_by('-completed_on')
        )
        if g4_records:
            activity_labels = [
                ('Comprehension', 'comprehension_score', 'comprehension_total'),
                ('Sequencing',    'sequencing_score',    'sequencing_total'),
                ('Inference',     'inference_score',     'inference_total'),
                ('Feelings',      'feelings_score',      'feelings_total'),
                ('Cause & Effect','cause_effect_score',  'cause_effect_total'),
                ('Main Lesson',   'theme_score',         'theme_total'),
            ]
            avg_activities = []
            for label, s_field, t_field in activity_labels:
                total_s = sum(getattr(r, s_field) for r in g4_records)
                total_t = sum(getattr(r, t_field) for r in g4_records)
                pct = round((total_s / total_t) * 100) if total_t else 0
                avg_activities.append({'label': label, 'pct': pct, 'score': total_s, 'total': total_t})
            avg_activities.sort(key=lambda x: x['pct'], reverse=True)
            g4_best2 = avg_activities[:2]
            g4_worst2 = avg_activities[-2:]
        avg_comprehension = g4_best2[0]['pct'] if g4_best2 else 0
        avg_visual = g4_worst2[-1]['pct'] if g4_worst2 else 0
        avg_spelling = 0
        if perfect_work:
            focus_label = 'Congratulations!'
            focus_tip = f'{child.name} got everything right. Celebrate this excellent work.'
        elif g4_worst2:
            focus_label = g4_worst2[-1]['label']
            focus_tip = f"Practise {g4_worst2[-1]['label'].lower()} questions to improve."
        else:
            focus_label = 'Keep going!'
            focus_tip = 'Complete more lessons to see your focus area.'
    else:
        avg_comprehension = round(
            sum(activity_percentage(record.comprehension_score, record.lesson.questions.all()) for record in records) / len(records)
        ) if records else 0
        avg_visual = round(
            sum(activity_percentage(record.visual_score, record.lesson.visual_items.all()) for record in records) / len(records)
        ) if records else 0
        avg_spelling = round(
            sum(activity_percentage(record.spelling_score, record.lesson.spelling_activities.all()) for record in records) / len(records)
        ) if records else 0
        activity_scores = [
            ('Reading', avg_comprehension, 'Comprehension and story questions'),
            ('Visual', avg_visual, 'Picture matching activities'),
            ('Spelling', avg_spelling, 'Copy writing and missing letters'),
        ]
        if perfect_work:
            focus_label = 'Congratulations!'
            focus_tip = f'{child.name} got everything right. Celebrate this excellent work.'
        else:
            focus_label, _, focus_tip = min(
                activity_scores,
                key=lambda item: item[1],
                default=('Reading', 0, 'Read aloud for five minutes each day.'),
            )

    return {
        'child': child,
        'learner': child,
        'teacher': child.teacher,
        'teacher_class': child.teacher_class,
        'lessons_done': lessons_done,
        'total_lessons': total_lessons,
        'progress_percent': min(progress_percent, 100),
        'average': average,
        'stars': stars,
        'latest': latest,
        'records': records,
        'avg_comprehension': avg_comprehension,
        'avg_visual': avg_visual,
        'avg_spelling': avg_spelling,
        'best_lesson': best_lesson,
        'best_score': best_score,
        'focus_area': focus_label,
        'focus_tip': focus_tip,
        'needs_help': bool(percentages) and average < 70,
        'perfect_work': perfect_work,
        'is_grade4': is_grade4,
        'g4_best2': g4_best2,
        'g4_worst2': g4_worst2,
    }

def subscription_page(request):
    """
    Shown right after registration (and reachable any time from the
    dashboard). Parents see individual/family/enterprise plan options; teachers/schools see
    the enterprise plan, framed as a government/district-funded package
    request rather than an instant card checkout.
    """
    role = request.session.get('account_role')
    if role not in ('parent', 'teacher'):
        messages.error(request, 'Please sign in first.')
        return redirect('/login')

    account_id = request.session['account_id']
    if role == 'parent':
        account = get_object_or_404(Parent, id=account_id)
        subscription, _ = Subscription.objects.get_or_create(
            parent=account, defaults={'plan_type': 'individual'}
        )
    else:
        account = get_object_or_404(Teacher, id=account_id)
        subscription, _ = Subscription.objects.get_or_create(
            teacher=account, defaults={'plan_type': 'enterprise'}
        )

    if request.method == 'POST':
        if role == 'parent':
            plan = request.POST.get('plan', 'individual')
            skip = request.POST.get('skip') == '1'

            if skip:
                subscription.status = 'trial'
                subscription.save(update_fields=['status', 'updated_at'])
                messages.success(request, "No problem — you're on a free trial. You can subscribe any time from your dashboard.")
                return redirect('/parent/dashboard')

            if plan == 'family':
                subscription.plan_type = 'family'
                subscription.billing_cycle = 'monthly'
                # No live payment gateway is wired up yet — this marks the
                # choice as pending until payment details are captured next.
                subscription.status = 'pending'
                subscription.save()
                return redirect('/subscription/payment')

            elif plan == 'enterprise':
                # Parent is redeeming an enterprise/school package code —
                # accept school name + package code and activate immediately
                school_name = request.POST.get('school_name', '').strip() or account.school_name
                code_value = request.POST.get('package_code', '').strip().upper()

                if not school_name or not code_value:
                    messages.error(request, 'Please enter both your school name and package code.')
                    return render(request, 'subscription.html', {'role': role, 'account': account, 'subscription': subscription})

                try:
                    code_obj = PackageCode.objects.get(code=code_value)
                except PackageCode.DoesNotExist:
                    code_obj = None

                if not code_obj or not code_obj.is_redeemable:
                    messages.error(request, "That package code isn't valid or has already been fully used. Please check the code from your district/government contact.")
                    return render(request, 'subscription.html', {'role': role, 'account': account, 'subscription': subscription})

                subscription.plan_type = 'enterprise'
                subscription.school_name = school_name
                subscription.package_code = code_obj
                subscription.status = 'active'
                subscription.save()

                code_obj.redemptions_count += 1
                code_obj.save(update_fields=['redemptions_count'])

                messages.success(request, f"Your school's package is active! {school_name} now has full SGILA access.")
                return redirect('/parent/dashboard')

            else:
                subscription.plan_type = 'individual'
                subscription.billing_cycle = 'monthly'
                # No live payment gateway is wired up yet — this marks the
                # choice as pending until payment details are captured next.
                subscription.status = 'pending'
                subscription.save()
                return redirect('/subscription/payment')

        else:  # teacher / school — redeem a government-issued package code
            school_name = request.POST.get('school_name', '').strip() or account.school_name
            code_value = request.POST.get('package_code', '').strip().upper()

            if not school_name or not code_value:
                messages.error(request, 'Please enter both your school name and package code.')
                return render(request, 'subscription.html', {'role': role, 'account': account, 'subscription': subscription})

            try:
                code_obj = PackageCode.objects.get(code=code_value)
            except PackageCode.DoesNotExist:
                code_obj = None

            if not code_obj or not code_obj.is_redeemable:
                messages.error(request, "That package code isn't valid or has already been fully used. Please check the code from your district/government contact.")
                return render(request, 'subscription.html', {'role': role, 'account': account, 'subscription': subscription})

            subscription.plan_type = 'enterprise'
            subscription.school_name = school_name
            subscription.package_code = code_obj
            subscription.status = 'active'
            subscription.save()

            code_obj.redemptions_count += 1
            code_obj.save(update_fields=['redemptions_count'])

            messages.success(request, f"Your school's package is active! {school_name} now has full SGILA access.")
            return redirect('/teacher/dashboard')

    return render(request, 'subscription.html', {
        'role': role,
        'account': account,
        'subscription': subscription,
    })


def subscription_payment_page(request):
    """
    Payment-details step for the individual (parent) plan, shown right
    after a plan is chosen on /subscription. Only parents with a pending
    individual subscription land here.

    SECURITY NOTE: this view intentionally does NOT persist a full card
    number, CVV, or full bank account number anywhere — only a masked
    summary (last 4 digits, expiry, name) is saved, purely so the parent
    and support team can recognise which payment method is on file. A
    production deployment must swap this out for a PCI-compliant gateway
    (e.g. PayFast) using their hosted/tokenised checkout, so raw card data
    is sent straight to the gateway and never touches this server at all.
    """
    if request.session.get('account_role') != 'parent':
        messages.error(request, 'Please sign in as a parent first.')
        return redirect('/login?role=parent')

    parent = get_object_or_404(Parent, id=request.session['account_id'])
    subscription, _ = Subscription.objects.get_or_create(
        parent=parent, defaults={'plan_type': 'individual'}
    )

    # Only makes sense once a plan has actually been chosen.
    if subscription.plan_type not in ('individual', 'family') or not subscription.billing_cycle:
        return redirect('/subscription')

    if request.method == 'POST':
        method = request.POST.get('payment_method', 'card')
        subscription.payment_method = method

        if method == 'card':
            name_on_card = request.POST.get('name_on_card', '').strip()
            card_number = re.sub(r'\D', '', request.POST.get('card_number', ''))
            expiry = request.POST.get('expiry', '').strip()

            if not name_on_card or len(card_number) < 12 or not expiry:
                messages.error(request, 'Please fill in all card details correctly.')
                return render(request, 'subscription_payment.html', {'subscription': subscription})

            subscription.payer_name = name_on_card
            subscription.card_last4 = card_number[-4:]
            subscription.card_expiry = expiry
            # CVV and the full card number are deliberately discarded here —
            # never written to the database.

        else:  # debit_order
            account_holder = request.POST.get('account_holder', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            account_number = re.sub(r'\D', '', request.POST.get('account_number', ''))
            branch_code = request.POST.get('branch_code', '').strip()

            if not account_holder or not bank_name or len(account_number) < 6:
                messages.error(request, 'Please fill in all bank details correctly.')
                return render(request, 'subscription_payment.html', {'subscription': subscription})

            subscription.payer_name = account_holder
            subscription.bank_name = bank_name
            subscription.account_last4 = account_number[-4:]
            subscription.branch_code = branch_code

        subscription.status = 'active'
        subscription.save()
        messages.success(request, "You're all set! Your SGILA subscription is active.")
        return redirect('/parent/dashboard')

    return render(request, 'subscription_payment.html', {'subscription': subscription})


def subscription_cancel_page(request):
    """
    Page where a signed-in parent or teacher can cancel their current
    subscription. POST will mark the subscription `status` as 'cancelled'
    and redirect the user back to their dashboard.
    """
    role = request.session.get('account_role')
    if role not in ('parent', 'teacher'):
        messages.error(request, 'Please sign in first.')
        return redirect('/login')

    account_id = request.session.get('account_id')
    if role == 'parent':
        account = get_object_or_404(Parent, id=account_id)
        subscription = get_object_or_404(Subscription, parent=account)
    else:
        account = get_object_or_404(Teacher, id=account_id)
        subscription = get_object_or_404(Subscription, teacher=account)

    if request.method == 'POST':
        # Simple confirmation flow: a single POST will cancel.
        subscription.status = 'cancelled'
        subscription.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Your subscription has been cancelled. You can reactivate any time from the Plan page.')
        return redirect('/parent/dashboard' if role == 'parent' else '/teacher/dashboard')

    return render(request, 'subscription_cancel.html', {
        'subscription': subscription,
        'role': role,
        'account': account,
    })

def assessment_percentage(rows, key):
    row = next((item for item in rows if item['key'] == key), None)
    return row['pct'] if row else 0


def dashboard_page(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    if not user_can_view_child(request, child):
        messages.error(request, 'You do not have access to that learner report.')
        return redirect_after_forbidden(request)

    lessons = list(Lesson.objects.filter(grade=child.grade).order_by('id'))
    records = list(
        Progress.objects.filter(child=child, lesson__grade=child.grade)
        .select_related('lesson')
        .prefetch_related(
            'lesson__reading_activities',
            'lesson__questions',
            'lesson__visual_items',
            'lesson__spelling_activities',
        )
        .order_by('-completed_on')
    )
    records_by_lesson = {record.lesson_id: record for record in records}
    story_rows = []
    for lesson in lessons:
        record = records_by_lesson.get(lesson.id)
        assessment_rows = rows_for_record(record) if record else []
        assessed_score = sum(item['score'] for item in assessment_rows)
        assessed_total = sum(item['total'] for item in assessment_rows)
        story_rows.append({
            'lesson': lesson,
            'record': record,
            'completed': bool(record),
            'assessment_count': len(assessment_rows),
            'percentage': round((assessed_score / assessed_total) * 100) if assessed_total else 0,
        })

    completed_count = sum(1 for item in story_rows if item['completed'])
    story_count = len(story_rows)
    progress_percent = round((completed_count / story_count) * 100) if story_count else 0
    search_query = request.GET.get('q', '').strip()
    sort_value = request.GET.get('sort', 'curriculum').strip()
    valid_sorts = {
        'curriculum', 'recent', 'oldest', 'stars_desc', 'stars_asc',
        'score_desc', 'score_asc', 'completed_first', 'incomplete_first',
        'title_asc', 'title_desc',
    }
    if sort_value not in valid_sorts:
        sort_value = 'curriculum'

    def completed_first_key(item):
        return (0 if item['completed'] else 1, item['lesson'].title.lower())

    if sort_value == 'recent':
        story_rows.sort(key=lambda item: (
            0 if item['completed'] else 1,
            -item['record'].completed_on.timestamp() if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'oldest':
        story_rows.sort(key=lambda item: (
            0 if item['completed'] else 1,
            item['record'].completed_on.timestamp() if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'stars_desc':
        story_rows.sort(key=lambda item: (
            *completed_first_key(item)[:1],
            -item['record'].stars_earned if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'stars_asc':
        story_rows.sort(key=lambda item: (
            *completed_first_key(item)[:1],
            item['record'].stars_earned if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'score_desc':
        story_rows.sort(key=lambda item: (
            *completed_first_key(item)[:1],
            -item['percentage'] if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'score_asc':
        story_rows.sort(key=lambda item: (
            *completed_first_key(item)[:1],
            item['percentage'] if item['record'] else 0,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'completed_first':
        story_rows.sort(key=completed_first_key)
    elif sort_value == 'incomplete_first':
        story_rows.sort(key=lambda item: (
            0 if not item['completed'] else 1,
            item['lesson'].title.lower(),
        ))
    elif sort_value == 'title_asc':
        story_rows.sort(key=lambda item: item['lesson'].title.lower())
    elif sort_value == 'title_desc':
        story_rows.sort(key=lambda item: item['lesson'].title.lower(), reverse=True)

    if search_query:
        search_term = search_query.casefold()
        story_rows = [
            item for item in story_rows
            if search_term in item['lesson'].title.casefold()
        ]

    role = request.session.get('account_role')
    role_label = {
        'teacher': 'Teacher dashboard',
        'learner': 'Learner dashboard',
        'parent': 'Parent dashboard',
    }.get(role, 'Progress dashboard')

    return render(request, 'dashboard.html', {
        'child': child,
        'story_rows': story_rows,
        'story_count': story_count,
        'completed_count': completed_count,
        'progress_percent': progress_percent,
        'total_stars': sum(record.stars_earned for record in records),
        'role_label': role_label,
        'search_query': search_query,
        'sort_value': sort_value,
        'visible_story_count': len(story_rows),
        # Only the child's own parent can pause/resume the learner profile —
        # a teacher viewing the same report should not see the control.
        'can_manage_activation': role == 'parent',
    })


@require_http_methods(['POST'])
def deactivate_child(request, child_id):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')

    child = get_object_or_404(Child, id=child_id)
    if not user_can_view_child(request, child):
        messages.error(request, 'You do not have access to that learner report.')
        return redirect_after_forbidden(request)

    if child.is_active:
        child.deactivate(Child.DEACTIVATED_MANUAL)
    messages.success(request, f'{child.name}\u2019s profile is paused. They will not be able to sign in until you reactivate it.')
    return redirect(f'/dashboard/{child.id}')


@require_http_methods(['POST'])
def reactivate_child(request, child_id):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')

    child = get_object_or_404(Child, id=child_id)
    if not user_can_view_child(request, child):
        messages.error(request, 'You do not have access to that learner report.')
        return redirect_after_forbidden(request)

    if not child.is_active:
        child.reactivate()
    messages.success(request, f'{child.name}\u2019s profile is active again.')
    return redirect(f'/dashboard/{child.id}')


def story_report_page(request, child_id, lesson_id):
    child = get_object_or_404(Child, id=child_id)
    if not user_can_view_child(request, child):
        messages.error(request, 'You do not have access to that learner report.')
        return redirect_after_forbidden(request)

    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    record = (
        Progress.objects.filter(child=child, lesson=lesson)
        .select_related('lesson')
        .prefetch_related(
            'lesson__reading_activities',
            'lesson__questions',
            'lesson__visual_items',
            'lesson__spelling_activities',
        )
        .order_by('-completed_on')
        .first()
    )
    if not record:
        messages.info(request, 'Complete this story to unlock its detailed report.')
        return redirect(f'/dashboard/{child.id}')

    breakdown = rows_for_record(record)
    report_score = sum(item['score'] for item in breakdown)
    report_total = sum(item['total'] for item in breakdown)
    report_percentage = round((report_score / report_total) * 100) if report_total else 0
    focus = min(breakdown, key=lambda item: (item['pct'], -item['total'])) if breakdown else None
    strength = max(breakdown, key=lambda item: (item['pct'], item['total'])) if breakdown else None
    perfect_work = bool(report_total) and report_score == report_total
    suggestions = sorted(
        (item for item in breakdown if item['pct'] < 70),
        key=lambda item: (item['pct'], -item['total'], item['label']),
    )
    diary_response = ReadingActivityResponse.objects.filter(
        child=child,
        lesson=lesson,
    ).first()

    return render(request, 'story_report.html', {
        'child': child,
        'lesson': lesson,
        'record': record,
        'breakdown': breakdown,
        'report_score': report_score,
        'report_total': report_total,
        'report_percentage': report_percentage,
        'focus': focus,
        'strength': strength,
        'perfect_work': perfect_work,
        'suggestions': suggestions,
        'diary_response': diary_response,
    })


def build_dashboard_row(child):
    access_allowed, access_reason = child_access_status(child)
    records = list(
        Progress.objects.filter(child=child)
        .select_related('lesson')
        .prefetch_related(
            'lesson__reading_activities',
            'lesson__questions',
            'lesson__visual_items',
            'lesson__spelling_activities',
        )
        .order_by('-completed_on')
    )
    lessons_done = len(records)
    record_percentages = {}
    for record in records:
        record_rows = rows_for_record(record)
        record_score = sum(item['score'] for item in record_rows)
        record_total = sum(item['total'] for item in record_rows)
        record_percentages[record.id] = (
            round((record_score / record_total) * 100) if record_total else 0
        )
    percentages = list(record_percentages.values())
    average = round(sum(percentages) / len(percentages)) if percentages else 0
    total_lessons = Lesson.objects.filter(grade=child.grade).count() or Lesson.objects.count()
    progress_percent = round((lessons_done / total_lessons) * 100) if total_lessons else 0
    stars = sum(record.stars_earned for record in records)
    latest = records[0] if records else None
    best_lesson = max(records, key=lambda record: record_percentages[record.id], default=None)
    best_score = record_percentages[best_lesson.id] if best_lesson else 0
    perfect_work = bool(records) and all(
        record_percentages[record.id] == 100
        for record in records
    )
    assessment_rows = aggregate_rows(records)

    if perfect_work:
        focus_label = 'Excellent work'
        focus_tip = f'{child.name} got every assessed skill correct.'
    elif assessment_rows:
        focus = min(assessment_rows, key=lambda item: (item['pct'], -item['total']))
        focus_label = focus['label']
        focus_tip = focus['tip']
    else:
        focus_label = 'Keep going'
        focus_tip = 'Complete a lesson to see the first focus area.'

    reading_rows = [
        item for item in assessment_rows
        if item['key'] not in {'visual_literacy', 'spelling'}
    ]
    reading_score = sum(item['score'] for item in reading_rows)
    reading_total = sum(item['total'] for item in reading_rows)
    avg_comprehension = round((reading_score / reading_total) * 100) if reading_total else 0

    return {
        'child': child,
        'learner': child,
        'access_allowed': access_allowed,
        'access_reason': access_reason,
        'teacher': child.teacher,
        'teacher_class': child.teacher_class,
        'lessons_done': lessons_done,
        'total_lessons': total_lessons,
        'progress_percent': min(progress_percent, 100),
        'average': average,
        'stars': stars,
        'latest': latest,
        'records': records,
        'avg_comprehension': avg_comprehension,
        'avg_visual': assessment_percentage(assessment_rows, 'visual_literacy'),
        'avg_spelling': assessment_percentage(assessment_rows, 'spelling'),
        'best_lesson': best_lesson,
        'best_score': best_score,
        'focus_area': focus_label,
        'focus_tip': focus_tip,
        'needs_help': bool(percentages) and average < 70,
        'perfect_work': perfect_work,
        'assessment_rows': assessment_rows,
        'needs_grade_confirmation': child.needs_grade_confirmation(),
        'suggested_grade': child.suggested_next_grade(),
    }


def parent_dashboard(request):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')
    parent = get_object_or_404(Parent, id=request.session['account_id'])
    if account_trial_expired(parent):
        return payment_due_response(request, {'role': 'parent'})
    children = Child.objects.filter(Q(parent=parent) | Q(parent_email__iexact=parent.email)).distinct().order_by('name')
    for child in children:
        # Self-heals the stored age against date_of_birth whenever a parent views
        # their dashboard, so it rolls over on birthdays even if the child hasn't
        # logged in themselves recently.
        child.refresh_age_if_stale()
    cards = [build_dashboard_row(child) for child in children]
    active_cards = [card for card in cards if card['lessons_done']]
    overall_average = round(sum(card['average'] for card in active_cards) / len(active_cards)) if active_cards else 0
    total_lessons_done = sum(card['lessons_done'] for card in cards)
    total_stars = sum(card['stars'] for card in cards)
    needs_help_count = sum(1 for card in cards if card['needs_help'])
    grade_confirmation_cards = [card for card in cards if card['needs_grade_confirmation']]

    return render(request, 'parent_dashboard.html', {
        'parent': parent,
        'cards': cards,
        'overall_average': overall_average,
        'total_lessons_done': total_lessons_done,
        'total_stars': total_stars,
        'needs_help_count': needs_help_count,
        'grade_confirmation_cards': grade_confirmation_cards,
        'children_access_allowed': subscription_allows_children(parent),
    })


def teacher_dashboard(request):
    if request.session.get('account_role') != 'teacher':
        return redirect('/login?role=teacher')
    teacher = get_object_or_404(Teacher, id=request.session['account_id'])
    if account_trial_expired(teacher):
        return payment_due_response(request, {'role': 'teacher'})
    teacher_classes = ensure_teacher_codes(teacher)
    learners = Child.objects.filter(
        Q(teacher=teacher) | Q(school_name__iexact=teacher.school_name)
    ).distinct().order_by('grade', 'name')
    grades = parse_grades(teacher.grades_taught)
    if grades:
        learners = learners.filter(grade__in=grades)

    learner_rows = [build_dashboard_row(learner) for learner in learners]
    active_rows = [row for row in learner_rows if row['lessons_done']]
    grade_sections = []
    for grade in sorted({row['learner'].grade for row in learner_rows}):
        rows = [row for row in learner_rows if row['learner'].grade == grade]
        active_grade_rows = [row for row in rows if row['lessons_done']]
        grade_sections.append({
            'grade': grade,
            'rows': rows,
            'class_average': round(
                sum(row['average'] for row in active_grade_rows) / len(active_grade_rows)
            ) if active_grade_rows else 0,
            'needs_help_count': sum(1 for row in rows if row['needs_help']),
        })

    class_average = round(sum(row['average'] for row in active_rows) / len(active_rows)) if active_rows else 0
    grade_confirmation_rows = [row for row in learner_rows if row['needs_grade_confirmation']]
    preview_learners = learner_rows[:3]
    first_grade_anchor = f"grade-section-{grade_sections[0]['grade']}" if grade_sections else ''
    return render(request, 'teacher_dashboard.html', {
        'teacher': teacher,
        'learner_rows': learner_rows,
        'grade_sections': grade_sections,
        'class_average': class_average,
        'total_learners': learners.count(),
        'total_lessons_done': sum(row['lessons_done'] for row in learner_rows),
        'total_stars': sum(row['stars'] for row in learner_rows),
        'needs_help_count': sum(1 for row in learner_rows if row['needs_help']),
        'preview_learners': preview_learners,
        'first_grade_anchor': first_grade_anchor,
        'teacher_classes': teacher_classes,
        'grade_confirmation_rows': grade_confirmation_rows,
    })


@require_http_methods(['POST'])
def confirm_child_grade(request, child_id):
    """Yearly grade-confirmation step (see Child.needs_grade_confirmation).

    The app never advances a learner's grade by itself. Once a new school year
    starts, the parent or teacher dashboard shows a prompt for each learner who
    hasn't been confirmed yet; this view applies exactly what they choose —
    moved up, repeated, or anything else — and logs it to GradeHistory.
    """
    role = request.session.get('account_role')

    if role == 'parent':
        parent = get_object_or_404(Parent, id=request.session['account_id'])
        child = Child.objects.filter(id=child_id).filter(
            Q(parent=parent) | Q(parent_email__iexact=parent.email)
        ).first()
        confirmed_by, confirmed_by_name, redirect_to = GradeHistory.PARENT, parent.full_name, '/parent/dashboard'
    elif role == 'teacher':
        teacher = get_object_or_404(Teacher, id=request.session['account_id'])
        child = Child.objects.filter(id=child_id).first()
        if child and not teacher_can_view_child(teacher, child):
            child = None
        confirmed_by, confirmed_by_name, redirect_to = GradeHistory.TEACHER, teacher.full_name, '/teacher/dashboard'
    else:
        return redirect('/login')

    if not child:
        messages.error(request, 'Learner profile not found or access denied.')
        return redirect(redirect_to)

    try:
        grade = int(request.POST.get('grade', ''))
    except (TypeError, ValueError):
        grade = None

    if grade not in (1, 2, 3, 4):
        messages.error(request, 'Please choose a valid grade (1 to 4).')
        return redirect(redirect_to)

    previous_grade = child.grade
    child.record_grade_confirmation(grade, confirmed_by=confirmed_by, confirmed_by_name=confirmed_by_name)

    if grade > previous_grade:
        messages.success(request, f'{child.name} is now set to Grade {grade}. Their lessons will update to match.')
    elif grade == previous_grade:
        messages.success(request, f'{child.name} stays in Grade {grade} this year.')
    else:
        messages.success(request, f'{child.name} has been moved back to Grade {grade}.')

    return redirect(redirect_to)


# ─────────────────────────────────────────────────────────────
# GRADE 4 ACTIVITY PAGES
# ─────────────────────────────────────────────────────────────

def vocabulary_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    words = lesson.vocabulary_questions.all()
    return render(request, 'vocabulary.html', {
        'lesson': lesson,
        'child': child,
        'words': words,
    })


def sequencing_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    activity = lesson.sequencing_activities.first()
    return render(request, 'sequencing.html', {
        'lesson': lesson,
        'child': child,
        'activity': activity,
    })


def inference_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    questions = lesson.inference_questions.all()
    return render(request, 'inference.html', {
        'lesson': lesson,
        'child': child,
        'total_questions': questions.count(),
    })


def prediction_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    question = lesson.prediction_questions.first()
    return render(request, 'prediction.html', {
        'lesson': lesson,
        'child': child,
        'question': question,
    })


def feelings_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    questions = lesson.feelings_questions.all()
    return render(request, 'feelings.html', {
        'lesson': lesson,
        'child': child,
        'total_questions': questions.count(),
    })


def cause_effect_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    pairs = lesson.cause_effect_pairs.all()
    return render(request, 'cause_effect.html', {
        'lesson': lesson,
        'child': child,
        'pairs': pairs,
    })


def theme_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    question = lesson.theme_questions.first()
    return render(request, 'theme.html', {
        'lesson': lesson,
        'child': child,
        'question': question,
    })


def written_response_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id, grade=child.grade)
    prompt = lesson.written_prompts.first()

    if request.method == 'POST':
        text = capitalize_first(request.POST.get('response_text', ''))
        # Written response counts as 1 mark for attempting it
        attempted = 1 if text else 0
        request.session[f'lesson_{lesson_id}_written_score'] = attempted
        request.session[f'lesson_{lesson_id}_written_total'] = 1
        request.session[f'lesson_{lesson_id}_written_text'] = text[:2000]
        request.session.modified = True
        return redirect(f'/lessons/{lesson_id}/results')

    return render(request, 'written_response.html', {
        'lesson': lesson,
        'child': child,
        'prompt': prompt,
    })


# ══════════════════════════════════════════════════════════════════
#  MESSAGING — Frontend HTML views
# ══════════════════════════════════════════════════════════════════

def _fmt_time(dt):
    """Human-friendly relative timestamp."""
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    diff = now - dt
    if diff.total_seconds() < 60:
        return 'Just now'
    if diff < timedelta(hours=1):
        return f"{int(diff.seconds // 60)}m ago"
    if diff < timedelta(hours=24):
        return dt.strftime('%H:%M')
    if diff < timedelta(days=7):
        return dt.strftime('%a %H:%M')
    return dt.strftime('%d %b')


def conversations_page(request):
    """
    GET /conversations
    Learner picker — shows all learners linked to the current parent or teacher.
    Clicking a learner opens the chat about that learner.
    """
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')

    if role not in ('parent', 'teacher') or not account_id:
        messages.error(request, 'Please sign in to access messages.')
        return redirect('/login')

    if role == 'parent':
        try:
            parent = Parent.objects.get(pk=account_id)
            children = Child.objects.filter(
                Q(parent_id=account_id) | Q(parent_email__iexact=parent.email)
            ).distinct().select_related('teacher')
        except Parent.DoesNotExist:
            children = Child.objects.none()
    else:
        children = Child.objects.filter(teacher_id=account_id).select_related('parent')

    opposite_role = 'teacher' if role == 'parent' else 'parent'
    conversations = []
    for child in children:
        last_msg = Message.objects.filter(child=child).order_by('-sent_at').first()
        unread_count = Message.objects.filter(
            child=child, sender_role=opposite_role, is_read=False
        ).count()

        other_name = (child.teacher.full_name if child.teacher else 'No teacher assigned') \
            if role == 'parent' else \
            (child.parent.full_name if child.parent else 'No parent linked')

        conversations.append({
            'child_id': child.id,
            'child_name': child.name,
            'child_grade': child.grade,
            'other_party_name': other_name,
            'last_message': {
                'body': (last_msg.body[:70] + '…') if last_msg and len(last_msg.body) > 70 else (last_msg.body if last_msg else ''),
                'sent_at_display': _fmt_time(last_msg.sent_at) if last_msg else '',
                'sender_role': last_msg.sender_role if last_msg else '',
            } if last_msg else None,
            'unread_count': unread_count,
        })

    conversations.sort(
        key=lambda c: c['last_message']['sent_at_display'] if c['last_message'] else '',
        reverse=True,
    )

    return render(request, 'conversations.html', {
        'conversations': conversations,
        'role': role,
    })


def chat_page(request, child_id):
    """
    GET /messages/<child_id>
    Chat screen between the current user and the other party about this learner.
    """
    role = request.session.get('account_role')
    account_id = request.session.get('account_id')

    if role not in ('parent', 'teacher') or not account_id:
        messages.error(request, 'Please sign in to access messages.')
        return redirect('/login')

    child = get_object_or_404(Child, pk=child_id)

    if role == 'parent':
        try:
            parent = Parent.objects.get(pk=account_id)
        except Parent.DoesNotExist:
            return redirect('/conversations')
        parent_ok = (child.parent_id == int(account_id)) or \
                    (child.parent_email and child.parent_email.lower() == parent.email.lower())
        if not parent_ok:
            messages.error(request, 'You do not have access to this conversation.')
            return redirect('/conversations')
        other_party_name = child.teacher.full_name if child.teacher else 'Teacher (not yet assigned)'
    else:
        if child.teacher_id != int(account_id):
            messages.error(request, 'This learner is not in your class.')
            return redirect('/conversations')
        other_party_name = child.parent.full_name if child.parent else 'Parent (not yet linked)'

    # Mark incoming messages as read
    opposite_role = 'teacher' if role == 'parent' else 'parent'
    Message.objects.filter(child=child, sender_role=opposite_role, is_read=False).update(is_read=True)

    msgs_qs = Message.objects.filter(child=child).select_related('sender_parent', 'sender_teacher')
    messages_list = []
    for m in msgs_qs:
        sender_name = (m.sender_parent.full_name if m.sender_parent else 'Parent') \
            if m.sender_role == 'parent' else \
            (m.sender_teacher.full_name if m.sender_teacher else 'Teacher')
        messages_list.append({
            'id': m.id,
            'sender_role': m.sender_role,
            'sender_name': sender_name,
            'body': m.body,
            'sent_at': m.sent_at.isoformat(),
            'sent_at_display': _fmt_time(m.sent_at),
            'is_read': m.is_read,
        })

    progress_qs = Progress.objects.filter(child=child)
    stars_total = sum(p.stars_earned for p in progress_qs)
    lessons_completed = progress_qs.count()

    return render(request, 'chat.html', {
        'child': child,
        'role': role,
        'other_party_name': other_party_name,
        'messages_list': messages_list,
        'stars_total': stars_total,
        'lessons_completed': lessons_completed,
    })
