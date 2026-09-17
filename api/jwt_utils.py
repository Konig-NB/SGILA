"""
SGILA JWT Utilities
-------------------
Handles creation and validation of JWT access tokens.
Tokens are signed with HS256 using the Django SECRET_KEY.

Token payload structure:
  sub        – account primary key (int)
  role       – 'parent' | 'teacher' | 'learner'
  email      – account email
  name       – account full name / child name
  grade      – grade (learner only, else null)
  exp        – expiry timestamp (UTC)
  iat        – issued-at timestamp (UTC)
"""
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = timedelta(hours=8)   # stays valid for a school day


def _secret():
    return settings.SECRET_KEY


def create_access_token(payload: dict) -> str:
    """
    Build and sign a JWT.
    `payload` should include: sub, role, email, name, grade (optional).
    exp and iat are added automatically.
    """
    now = datetime.now(tz=timezone.utc)
    data = {
        **payload,
        "iat": now,
        "exp": now + ACCESS_TOKEN_LIFETIME,
    }
    return jwt.encode(data, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Returns the payload dict on success.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, _secret(), algorithms=[ALGORITHM])


def token_from_request(request):
    """
    Extract the JWT from the Authorization header ('Bearer <token>')
    or from the 'jwt_token' cookie (used by server-rendered pages).
    Returns the decoded payload or None.
    """
    # 1. Try Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # 2. Fall back to cookie (for HTML pages)
        token = request.COOKIES.get("jwt_token", "")

    if not token:
        return None

    try:
        return decode_access_token(token)
    except jwt.PyJWTError:
        return None


def require_jwt(roles=None):
    """
    Decorator factory for API views.
    Usage:
        @require_jwt(roles=['parent', 'teacher'])
        def my_view(request, payload, ...):
            ...

    `payload` is injected as the second positional argument.
    Returns 401 if no valid token, 403 if role not allowed.
    """
    from functools import wraps
    from django.http import JsonResponse

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            payload = token_from_request(request)
            if payload is None:
                return JsonResponse(
                    {"error": "Authentication required. Please log in."},
                    status=401,
                )
            if roles and payload.get("role") not in roles:
                return JsonResponse(
                    {"error": "You do not have permission to access this resource."},
                    status=403,
                )
            role = payload.get("role")
            account_id = payload.get("sub")
            if role == "parent":
                from .models import Parent

                parent = Parent.objects.filter(pk=account_id).only("is_active", "auth_version").first()
                if (
                    not parent
                    or not parent.is_active
                    or payload.get("auth_version", 0) != parent.auth_version
                ):
                    return JsonResponse({"error": "This account is deactivated or the session has expired."}, status=403)
            elif role == "teacher":
                from .models import Teacher

                teacher = Teacher.objects.filter(pk=account_id).only("is_active", "auth_version").first()
                if (
                    not teacher
                    or not teacher.is_active
                    or payload.get("auth_version", 0) != teacher.auth_version
                ):
                    return JsonResponse({"error": "This account is deactivated or the session has expired."}, status=403)
            elif role == "learner":
                from .account_access import child_access_status, linked_parent_for_child
                from .models import Child

                child = Child.objects.select_related("parent").filter(pk=account_id).first()
                if not child:
                    return JsonResponse({"error": "Learner account not found."}, status=403)
                allowed, reason = child_access_status(child)
                parent = linked_parent_for_child(child)
                if not allowed or (
                    parent
                    and payload.get("parent_auth_version", 0) != parent.auth_version
                ):
                    return JsonResponse({"error": "Learner access is paused.", "reason": reason}, status=403)
            return view_func(request, payload, *args, **kwargs)
        return _wrapped
    return decorator
