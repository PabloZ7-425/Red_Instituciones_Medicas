"""Isolated identity tests. Never use legacy SQLite or the live identity DB as a test DB."""
import os

from config.settings import *  # noqa: F403
from config.settings import _identity

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
if os.getenv("TEST_IDENTITY_POSTGRES") == "1":
    DATABASES = {"default": {
        **_identity,
        "USER": "identidad_migrator",
        "PASSWORD": os.environ["IDENTITY_MIGRATOR_PASSWORD"],
        "TEST": {"NAME": "test_b2_identidad"},
    }}

# Fast hashing in tests only; production uses Django's default PBKDF2.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES["legacy_fixture"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
