import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.historiales",
    "apps.identidad",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Identity cutover is explicit. Legacy remains available for inventory/rollback;
# no startup process migrates or copies accounts automatically.
IDENTITY_DB_MODE = os.getenv("IDENTITY_DB_MODE", "legacy")
if IDENTITY_DB_MODE not in {"legacy", "postgres"}:
    raise ValueError("IDENTITY_DB_MODE debe ser legacy o postgres")

_legacy = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}
_identity = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("IDENTITY_DB_NAME", "identidad"),
    "HOST": os.getenv("IDENTITY_DB_HOST", "identidad"),
    "PORT": os.getenv("IDENTITY_DB_PORT", "5432"),
    "USER": "identidad_app",
    "PASSWORD": os.getenv("IDENTITY_APP_PASSWORD", ""),
    "CONN_MAX_AGE": 0,
    "OPTIONS": {"connect_timeout": 3},
}
# The delivery deployment places identity in a dedicated schema inside hospital.
# An explicit public schema remains supported only for the old installation/rollback.
_identity_schema = os.getenv("IDENTITY_DB_SCHEMA", "public")
if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", _identity_schema):
    raise ValueError("IDENTITY_DB_SCHEMA invalido")
_identity["OPTIONS"]["options"] = "-c search_path=" + _identity_schema
DATABASES = {
    "default": _identity if IDENTITY_DB_MODE == "postgres" else _legacy.copy(),
    "identity_migration": {
        **_identity, "USER": "identidad_migrator",
        "PASSWORD": os.getenv("IDENTITY_MIGRATOR_PASSWORD", ""),
    }
}
# Read-only legacy alias: use only after backup, never for migrate/loaddata.
DATABASES["legacy"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": "file:" + Path(os.getenv("IDENTITY_LEGACY_PATH", str(BASE_DIR / "db.sqlite3"))).resolve().as_posix() + "?mode=ro",
    "OPTIONS": {"uri": True},
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "es-gt"
TIME_ZONE = "America/Guatemala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]
CSRF_FAILURE_VIEW = "apps.identidad.http.csrf_failure"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.getenv("DJANGO_COOKIE_SECURE", str(not DEBUG)).lower() == "true"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.identidad.http.exception_handler",
}
