"""
Frontend views for the SGILA web app.

The API module exposes JSON endpoints. These views render the role-aware
application screens described in the supplied wireframes and data-flow docs.
"""
import hashlib
import json
import random
import re
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from api.models import (
    CauseEffectPair,
    Child,
    ComprehensionQuestion,
    FeelingsQuestion,
    Grade4ActivityProgress,
    InferenceQuestion,
    Lesson,
    Message,
    Parent,
    PredictionQuestion,
    Progress,
    SequencingActivity,
    SpellingActivity,
    Teacher,
    TeacherClass,
    ThemeQuestion,
    VocabularyQuestion,
    WrittenResponsePrompt,
    generate_class_code,
    OTPToken,
    PasswordResetToken,
)


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


def learner_required(request):
    child_id = request.session.get('child_id')
    if not child_id:
        messages.error(request, 'Please sign in as a learner first.')
        return None, redirect('/login?role=learner')
    return get_object_or_404(Child, id=child_id), None


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
    return username[:40]


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
    set_account_session(request, 'learner', child, child)
    return redirect(f'/grade/{child.grade}')


def register_parent(request):
    data = request.POST
    email = data['email'].strip().lower()
    full_name = data.get('full_name', '').strip()

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
    full_name = data.get('full_name', '').strip()

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
        'school_name': data.get('school_name', '').strip(),
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
                set_account_session(request, role, account, account)
                return redirect(f'/grade/{account.grade}')
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

            Child.objects.create(
                parent=parent,
                username=username,
                first_name=first_name,
                last_name=last_name,
                name=child_name,
                age=int(request.POST['age']),
                grade=int(request.POST['grade']),
                school_name=request.POST.get('school_name', '').strip() or (teacher.school_name if teacher else ''),
                parent_email=parent.email,
                photo=request.FILES.get('photo'),
                password=make_password(request.POST['password']),
                teacher=teacher,
                teacher_class=teacher_class,
            )
            messages.success(request, 'Child profile added.')
            return redirect('/parent/dashboard')

    return render(request, 'add_child.html', {'parent': parent})


@require_http_methods(['POST'])
def parent_delete_child(request, child_id):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')
    parent = get_object_or_404(Parent, id=request.session['account_id'])
    child = Child.objects.filter(
        id=child_id,
    ).filter(
        Q(parent=parent) | Q(parent_email__iexact=parent.email)
    ).first()
    if not child:
        messages.error(request, 'Child profile not found or access denied.')
        return redirect('/parent/dashboard')

    child.delete()
    messages.success(request, 'Child profile deleted permanently.')
    return redirect('/parent/dashboard')


def grade_home(request, grade):
    child, response = learner_required(request)
    if response:
        return response

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

    lessons = Lesson.objects.filter(grade=grade).order_by('id')
    records = Progress.objects.filter(child=child)
    progress_by_lesson = {record.lesson_id: record for record in records}
    lesson_data = []
    for lesson in lessons:
        record = progress_by_lesson.get(lesson.id)
        lesson_data.append({
            'id': lesson.id,
            'title': lesson.title,
            'grade': lesson.grade,
            'thumbnail_image': lesson.thumbnail_image,
            'completed': bool(record),
            'stars': range(record.stars_earned) if record else range(0),
        })
    return render(request, 'grade_home.html', {
        'lessons': lesson_data,
        'grade': grade,
        'child': child,
        'child_name': child.name,
        'completed_count': records.count(),
        'total_stars': sum(r.stars_earned for r in records),
    })


def story_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
    pages = [{
        'page_number': p.page_number,
        'text': p.text,
        'image_url': p.image_url,
        'audio_url': p.audio_url,
        'highlighted_words': p.get_highlighted_words(),
    } for p in lesson.pages.all()]
    if lesson.grade == 4:
        first_activity_url = f'/lessons/{lesson_id}/questions'
    else:
        first_activity_url = f'/lessons/{lesson_id}/questions'
    return render(request, 'story.html', {
        'lesson': lesson,
        'pages': pages,
        'child': child,
        'first_activity_url': first_activity_url,
    })


def questions_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
    total_questions = ComprehensionQuestion.objects.filter(lesson=lesson).count()
    return render(request, 'questions.html', {
        'lesson': lesson,
        'lesson_id': lesson_id,
        'child_id': child.id,
        'total_questions': total_questions,
    })


def visual_activity_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return render(request, 'visual_activity.html', {
        'lesson': lesson,
        'child': child,
        'items': lesson.visual_items.all(),
    })


def pronunciation_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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


def results_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
        seq_score   = gs('seq_score');            seq_total   = gs('seq_total',   1)
        # Activity 3 — Inference
        inf_score   = gs('inference_score');      inf_total   = gs('inference_total',   lesson.inference_questions.count())
        # Activity 4 — Feelings
        feel_score  = gs('feelings_score');       feel_total  = gs('feelings_total',  lesson.feelings_questions.count())
        # Activity 5 — Cause & Effect
        ce_score    = gs('ce_score');             ce_total    = gs('ce_total',    lesson.cause_effect_pairs.count())
        # Activity 6 — Theme / Main Lesson
        theme_score = gs('theme_score');          theme_total = gs('theme_total', 1)

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

        breakdown = [
            {'label': 'Comprehension',  'score': comp_score,  'total': comp_total},
            {'label': 'Sequencing',     'score': seq_score,   'total': seq_total},
            {'label': 'Inference',      'score': inf_score,   'total': inf_total},
            {'label': 'Feelings',       'score': feel_score,  'total': feel_total},
            {'label': 'Cause & Effect', 'score': ce_score,    'total': ce_total},
            {'label': 'Main Lesson',    'score': theme_score, 'total': theme_total},
        ]
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


def dashboard_page(request, child_id):
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


def build_dashboard_row(child):
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


def parent_dashboard(request):
    if request.session.get('account_role') != 'parent':
        return redirect('/login?role=parent')
    parent = get_object_or_404(Parent, id=request.session['account_id'])
    children = Child.objects.filter(Q(parent=parent) | Q(parent_email__iexact=parent.email)).distinct().order_by('name')
    cards = [build_dashboard_row(child) for child in children]
    active_cards = [card for card in cards if card['lessons_done']]
    overall_average = round(sum(card['average'] for card in active_cards) / len(active_cards)) if active_cards else 0
    total_lessons_done = sum(card['lessons_done'] for card in cards)
    total_stars = sum(card['stars'] for card in cards)
    needs_help_count = sum(1 for card in cards if card['needs_help'])

    return render(request, 'parent_dashboard.html', {
        'parent': parent,
        'cards': cards,
        'overall_average': overall_average,
        'total_lessons_done': total_lessons_done,
        'total_stars': total_stars,
        'needs_help_count': needs_help_count,
    })


def teacher_dashboard(request):
    if request.session.get('account_role') != 'teacher':
        return redirect('/login?role=teacher')
    teacher = get_object_or_404(Teacher, id=request.session['account_id'])
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
    return render(request, 'teacher_dashboard.html', {
        'teacher': teacher,
        'learner_rows': learner_rows,
        'grade_sections': grade_sections,
        'class_average': class_average,
        'total_learners': learners.count(),
        'total_lessons_done': sum(row['lessons_done'] for row in learner_rows),
        'total_stars': sum(row['stars'] for row in learner_rows),
        'needs_help_count': sum(1 for row in learner_rows if row['needs_help']),
        'teacher_classes': teacher_classes,
    })


# ─────────────────────────────────────────────────────────────
# GRADE 4 ACTIVITY PAGES
# ─────────────────────────────────────────────────────────────

def vocabulary_page(request, lesson_id):
    child, response = learner_required(request)
    if response:
        return response
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
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
    lesson = get_object_or_404(Lesson, id=lesson_id)
    prompt = lesson.written_prompts.first()

    if request.method == 'POST':
        text = request.POST.get('response_text', '').strip()
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
