"""Django settings for the U.O.R web migration backend.

The backend is deliberately connected to the existing MySQL database and the
models are unmanaged, so no desktop data is replaced during the migration.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATION_ROOT = BASE_DIR.parent
WEB_LEGACY_SRC = BASE_DIR / "legacy_src"

# Load order:
# 1. Web_app_migration/.env is the shared web migration configuration.
# 2. Web_app_migration/backend/.env can override backend-only values locally.
load_dotenv(MIGRATION_ROOT / ".env", override=True)
load_dotenv(BASE_DIR / ".env", override=True)

WEB_STORAGE_ROOT = Path(os.getenv("WEB_STORAGE_ROOT") or MIGRATION_ROOT / "storage")

# Backward-compatible names used by the migration bridge. They now point inside
# Web_app_migration so the web app does not depend on the desktop project root.
LEGACY_PROJECT_ROOT = WEB_LEGACY_SRC
LEGACY_STORAGE_ROOT = WEB_STORAGE_ROOT

if str(WEB_LEGACY_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_LEGACY_SRC))


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", os.getenv("DEBUG", "False")).lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

ACCESS_APPROVAL_BASE_URL = os.getenv("ACCESS_APPROVAL_BASE_URL", "").rstrip("/")
ACCESS_APPROVAL_TUNNEL_PROVIDER = os.getenv("ACCESS_APPROVAL_TUNNEL_PROVIDER", "localtunnel").strip().lower()

approval_host = urlparse(ACCESS_APPROVAL_BASE_URL).hostname if ACCESS_APPROVAL_BASE_URL else ""
for host in (approval_host, ".loca.lt" if ACCESS_APPROVAL_TUNNEL_PROVIDER == "localtunnel" else ""):
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

INSTALLED_APPS = [
    "corsheaders",
    "apps.runtime.apps.RuntimeConfig",
    "apps.data.apps.DataConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.students.apps.StudentsConfig",
    "apps.finance.apps.FinanceConfig",
    "apps.access_control.apps.AccessControlConfig",
    "apps.transfers.apps.TransfersConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.academics.apps.AcademicsConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "web_config.urls"
ASGI_APPLICATION = "web_config.asgi.application"
WSGI_APPLICATION = "web_config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "mysql.connector.django",
        "NAME": os.getenv("DB_NAME", "uor_university"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.getenv("TZ", "Africa/Kinshasa")
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = WEB_STORAGE_ROOT

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "3600"))
FRONTEND_URL = os.getenv("WEB_FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
BACKEND_PUBLIC_URL = os.getenv("WEB_BACKEND_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")

ACCESS_SERVER_AUTOSTART = env_bool("ACCESS_SERVER_AUTOSTART", True)
ACCESS_APPROVAL_AUTOSTART = env_bool("ACCESS_APPROVAL_AUTOSTART", True)
ACCESS_APPROVAL_TUNNEL_AUTOSTART = env_bool("ACCESS_APPROVAL_TUNNEL_AUTOSTART", True)
ACCESS_APPROVAL_TUNNEL_PORT = env_int("ACCESS_APPROVAL_TUNNEL_PORT", 8000)
ACCESS_APPROVAL_TUNNEL_HOST = os.getenv("ACCESS_APPROVAL_TUNNEL_HOST", "127.0.0.1").strip() or "127.0.0.1"
ACCESS_APPROVAL_TUNNEL_SUBDOMAIN = os.getenv("ACCESS_APPROVAL_TUNNEL_SUBDOMAIN", "").strip()

MIGRATION_MODULES = {
    "runtime": None,
    "accounts": None,
    "dashboard": None,
    "students": None,
    "finance": None,
    "access_control": None,
    "transfers": None,
    "notifications": None,
    "reports": None,
    "academics": None,
    "data": None,
}
