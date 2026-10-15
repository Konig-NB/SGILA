from django.core.exceptions import ImproperlyConfigured
from pathlib import Path
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env(path):
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


dot_env_path = BASE_DIR / '.env'
load_local_env(dot_env_path)

# Older local copies of SGILA used a file named ``env``. Keep it as a
# backwards-compatible fallback so existing installations do not silently
# lose their mail and API configuration. A real .env always takes precedence.
if not dot_env_path.exists():
    load_local_env(BASE_DIR / 'env')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
_secret_key = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not DEBUG and not _secret_key:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is disabled.')
SECRET_KEY = _secret_key or 'sgila-local-development-key-change-before-deployment-2026'

_render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
_default_allowed_hosts = '127.0.0.1,localhost,testserver' if DEBUG else ''
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', _default_allowed_hosts).split(',')
    if host.strip()
]
if _render_hostname and _render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_hostname)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'Set DJANGO_ALLOWED_HOSTS or deploy with RENDER_EXTERNAL_HOSTNAME.'
    )

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if _render_hostname:
    _render_origin = f'https://{_render_hostname}'
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'api',
    'lessons',
    'schools',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lessons.middleware.AccountAccessMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sgila_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'lessons.context_processors.unread_messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sgila_project.wsgi.application'

_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        )
    }
else:
    _db_engine = os.environ.get('DB_ENGINE', 'postgresql').lower()
    if _db_engine in {'postgres', 'postgresql'}:
        _db_name = os.environ.get('DB_NAME')
        _db_user = os.environ.get('DB_USER')
        _db_password = os.environ.get('DB_PASSWORD')
        if not _db_name or not _db_user or _db_password is None:
            raise ImproperlyConfigured(
                'Set DB_NAME, DB_USER, and DB_PASSWORD, or provide DATABASE_URL, '
                'for PostgreSQL.'
            )
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': _db_name,
                'USER': _db_user,
                'PASSWORD': _db_password,
                'HOST': os.environ.get('DB_HOST', 'localhost'),
                'PORT': os.environ.get('DB_PORT', '5432'),
                'CONN_MAX_AGE': 600,
                'CONN_HEALTH_CHECKS': True,
            }
        }
    elif _db_engine == 'sqlite':
        if not DEBUG:
            raise ImproperlyConfigured('SQLite is only supported for local development.')
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
    else:
        raise ImproperlyConfigured(
            'DB_ENGINE must be postgresql or sqlite.'
        )

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ENABLE_STORY_THRESHOLDS = False

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', str(not DEBUG)).lower() in {'1', 'true', 'yes', 'on'}
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'help_ticket': '5/hour',
        'feedback': '5/hour',
    },
}

# EMAIL (OTP delivery)
# Use SMTP automatically when credentials are present. Otherwise, keep the
# clean-machine behaviour of printing messages to the terminal.
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in {
    '1', 'true', 'yes', 'on'
}
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
_email_password_is_placeholder = any(
    marker in EMAIL_HOST_PASSWORD.lower()
    for marker in ('paste-your', 'app-password', 'replace', 'placeholder')
)
_smtp_is_configured = bool(
    EMAIL_HOST_USER and EMAIL_HOST_PASSWORD and not _email_password_is_placeholder
)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    (
        'django.core.mail.backends.smtp.EmailBackend'
        if _smtp_is_configured
        else 'django.core.mail.backends.console.EmailBackend'
    ),
)
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'SGILA <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'SGILA <noreply@localhost>',
)
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'sgila.info@gmail.com')

# ─── JWT ───────────────────────────────────────────────────────────────────────
# Access tokens are signed with SECRET_KEY via HS256.
# In production set SECRET_KEY from an environment variable — never commit it.
JWT_ACCESS_TOKEN_LIFETIME_HOURS = 8  # informational; enforced in api/jwt_utils.py

# Base URL used in password-reset emails
SITE_URL = os.environ.get(
    'SITE_URL',
    f'https://{_render_hostname}' if _render_hostname else 'http://127.0.0.1:8000',
)

# ─── Individual & Family plan pricing ──────────────────────────────────────────
# The two card-paid plans, in rand per month. Same rule as the Enterprise table
# below: these numbers live here and nowhere else, and ``lessons.pricing``
# renders them for the plan cards. 'enterprise' is deliberately absent — it is
# priced per learner from the school-quintile table, not from a flat monthly fee.
SUBSCRIPTION_PRICES = {
    'individual': 49,
    'family': 89,
}

# ─── Enterprise (school) pricing ───────────────────────────────────────────────
# Single source of truth for Enterprise pricing. Nothing in a template or in
# JavaScript may repeat these numbers — templates read the values rendered by
# ``lessons.pricing`` and the calculator's live figures come from the
# ``/subscription/enterprise-pricing`` JSON endpoint, which calls the same
# module. Change anything here and the Enterprise card and the pricing dialog
# both follow automatically.
#
# School types are the Department of Basic Education's poverty ranking:
# Quintile 1 is the poorest, Quintile 5 the least poor. Private/independent
# schools sit outside that ranking.
SCHOOL_TYPES = [
    ('quintile_1', 'Quintile 1 (poorest)'),
    ('quintile_2', 'Quintile 2'),
    ('quintile_3', 'Quintile 3'),
    ('quintile_4', 'Quintile 4'),
    ('quintile_5', 'Quintile 5 (least poor)'),
    ('private', 'Private / independent school'),
]

# Smallest number of learners an Enterprise package can be sold to.
MINIMUM_LEARNERS = 100

# Which way round the quintile pricing runs:
#   'government_funded' (default) — poorer schools (lower quintiles) receive
#       more state funding and need more learning support, so they pay MORE per
#       learner. Quintile 5 and private schools get our lowest rate.
#   'school_paid' — the alternative model, where price rises with the school's
#       own ability to pay, so Quintile 1 gets our lowest rate.
# Values are rand per learner per month.
PRICING_MODE = os.environ.get('SGILA_PRICING_MODE', 'government_funded')

PRICE_PER_LEARNER_MONTH = {
    'government_funded': {
        'quintile_1': 40,
        'quintile_2': 35,
        'quintile_3': 30,
        'quintile_4': 25,
        'quintile_5': 20,
        'private': 20,
    },
    'school_paid': {
        'quintile_1': 20,
        'quintile_2': 25,
        'quintile_3': 30,
        'quintile_4': 35,
        'quintile_5': 40,
        'private': 40,
    },
}

# Optional annual prepay discount, off by default. Set the number of months a
# school is actually charged for when paying a year up front; None or leaving it
# unset means "no discount", and the dialog then shows the monthly billing total
# only. The canonical example is 10 — pay 10 months, get 12.
ANNUAL_PREPAY_MONTHS_BILLED = None

# The "From R.../month per learner" figure on the Enterprise card. Derived from
# the active mode's table rather than typed in, so the card can never disagree
# with the calculator. Set ENTERPRISE_START_PRICE_PER_LEARNER_MONTH explicitly
# below this line only if you deliberately want an advertised floor that isn't
# a real school type price.
_ACTIVE_PRICES = PRICE_PER_LEARNER_MONTH.get(PRICING_MODE)
if _ACTIVE_PRICES is None:
    raise ImproperlyConfigured(
        f'PRICING_MODE must be one of {sorted(PRICE_PER_LEARNER_MONTH)}, got {PRICING_MODE!r}.'
    )
ENTERPRISE_START_PRICE_PER_LEARNER_MONTH = min(_ACTIVE_PRICES.values())

# ─── School finder (DBE National Master List of Schools) ──────────────────────
# The nine provinces, in the DBE's own spelling. Used as the canonical list by
# ``schools.import_schools`` (to normalise whatever the source file says), by the
# School model's province choices, and by the province dropdown in the UI — so
# "KwaZulu-Natal" is spelled the same way everywhere.
PROVINCES = [
    'Eastern Cape',
    'Free State',
    'Gauteng',
    'KwaZulu-Natal',
    'Limpopo',
    'Mpumalanga',
    'Northern Cape',
    'North West',
    'Western Cape',
]

# Alternate spellings seen in older master-list exports, normalised on import.
PROVINCE_ALIASES = {
    'kwazulu natal': 'KwaZulu-Natal',
    'kwazulunatal': 'KwaZulu-Natal',
    'kzn': 'KwaZulu-Natal',
    'natal': 'KwaZulu-Natal',
    'eastern cape': 'Eastern Cape',
    'e cape': 'Eastern Cape',
    'cape': 'Eastern Cape',
    'free state': 'Free State',
    'gauteng': 'Gauteng',
    'gauteng province': 'Gauteng',
    'limpopo': 'Limpopo',
    'mpumalanga': 'Mpumalanga',
    'mpumalanga province': 'Mpumalanga',
    'northern cape': 'Northern Cape',
    'n cape': 'Northern Cape',
    'north west': 'North West',
    'northwest': 'North West',
    'n west': 'North West',
    'western cape': 'Western Cape',
    'w cape': 'Western Cape',
}

# Default location of the cleaned master list, used when ``import_schools`` is
# called with no argument.
SCHOOLS_DATA_PATH = BASE_DIR / 'data' / 'schools_master_list_clean.csv'

# ─── School finder throttling ─────────────────────────────────────────────────
# The autocomplete is public and unauthenticated, so it is rate limited per IP to
# keep it from being scraped. ``SCHOOLS_SEARCH_RATE_LIMIT`` calls per
# ``SCHOOLS_SEARCH_RATE_WINDOW`` seconds.
SCHOOLS_SEARCH_RATE_LIMIT = 60
SCHOOLS_SEARCH_RATE_WINDOW = 60

# ─── AI story generation (Gemini text + Pollinations illustrations) ────────────
# Leave GEMINI_API_KEY blank to keep the feature disabled. The request path
# creates a provider client only when a configured AI feature is actually used,
# so ordinary startup and test runs never require an API key.
# ─── AI story generation ─────────────────────────────────────────────────────
# Grade 4 uses Groq for text and Pollinations with Cloudflare Workers AI as an
# image fallback. Other grades retain their existing Gemini/Pollinations path.
# All providers are called with plain HTTPS requests (see lessons/views.py).
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'qwen/qwen3.8-27b')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-flash-lite-latest')
POLLINATIONS_MODEL = os.environ.get('POLLINATIONS_MODEL', 'flux')
POLLINATIONS_API_KEY = os.environ.get('POLLINATIONS_API_KEY', '')
CLOUDFLARE_ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')
CLOUDFLARE_API_TOKEN = os.environ.get('CLOUDFLARE_API_TOKEN', '')
CLOUDFLARE_IMAGE_MODEL = os.environ.get(
    'CLOUDFLARE_IMAGE_MODEL', '@cf/black-forest-labs/flux-1-schnell',
)
