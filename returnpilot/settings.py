import os
import sys
import tempfile
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-returnpilot-default-secret-key-change-in-production",
)

# Production Railway detection
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_STATIC_URL"))

if IS_RAILWAY:
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes", "t")
    ALLOWED_HOSTS = ["*"]
else:
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes", "t")
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    # Local apps
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "returnpilot.urls"

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            FRONTEND_DIST,
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "returnpilot.wsgi.application"
ASGI_APPLICATION = "returnpilot.asgi.application"


# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
elif DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = []
if (FRONTEND_DIST / "assets").exists():
    STATICFILES_DIRS.append(FRONTEND_DIST / "assets")

# CORS configuration
#
# Local dev (DEBUG) allows all origins for convenience. In production the browser
# origins that may call the API must be listed explicitly — either via the built-in
# localhost defaults or the CORS_ALLOWED_ORIGINS env var (comma-separated). We no
# longer open CORS wide just because we are on Railway.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra_cors = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if _extra_cors:
    CORS_ALLOWED_ORIGINS += [o.strip() for o in _extra_cors.split(",") if o.strip()]

CORS_ALLOW_ALL_ORIGINS = DEBUG

# Trust the same explicit origins for CSRF (needed for session-authenticated POSTs
# from the SPA when served cross-origin, e.g. behind a Railway domain).
CSRF_TRUSTED_ORIGINS = [
    o for o in CORS_ALLOWED_ORIGINS if o.startswith("http://") or o.startswith("https://")
]
_railway_static_url = os.getenv("RAILWAY_STATIC_URL")
if _railway_static_url:
    origin = _railway_static_url if "://" in _railway_static_url else f"https://{_railway_static_url}"
    CSRF_TRUSTED_ORIGINS.append(origin)

# Django REST Framework
#
# Authentication is opt-in: set REQUIRE_API_AUTH=True to require a valid token (or an
# authenticated session) on every endpoint that doesn't override its own permissions.
# Left off, the API stays AllowAny — matching the historical closed-environment posture
# and keeping the test suite / local dev friction-free.
REQUIRE_API_AUTH = os.getenv("REQUIRE_API_AUTH", "False").lower() in ("true", "1", "yes", "t")
_default_permission = (
    "rest_framework.permissions.IsAuthenticated"
    if REQUIRE_API_AUTH
    else "rest_framework.permissions.AllowAny"
)

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [_default_permission],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Configuration
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
if "test" in sys.argv:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Google Cloud / Vertex AI Settings
GCP_CREDENTIALS_JSON = os.getenv("GCP_CREDENTIALS_JSON")
if GCP_CREDENTIALS_JSON:
    try:
        temp_cred = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        temp_cred.write(GCP_CREDENTIALS_JSON)
        temp_cred.flush()
        temp_cred.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_cred.name
    except Exception as e:
        print(f"Warning: Failed writing GCP_CREDENTIALS_JSON: {e}")
else:
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if GOOGLE_APPLICATION_CREDENTIALS:
        cred_path = Path(GOOGLE_APPLICATION_CREDENTIALS)
        if not cred_path.is_absolute():
            cred_path = (BASE_DIR / cred_path).resolve()
        if cred_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "ai-projects-500402")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
