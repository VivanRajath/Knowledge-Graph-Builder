import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret')
# Force DEBUG for local development unless explicitly disabled
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')
# Keep ALLOWED_HOSTS minimal for local runs; allow override via env
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Make optional dependencies optional so the project can run locally without
# installing everything from requirements.txt. If `rest_framework` is
# available, register it; otherwise skip it.
try:
    import rest_framework  # type: ignore
except Exception:
    pass
else:
    INSTALLED_APPS.append('rest_framework')

# Use the explicit app path for the Django app to avoid ambiguity between the
# repository-level `ontologies` package and the Django app package.
INSTALLED_APPS.append('django_backend.ontologies')

MIDDLEWARE = [
    # 'django_backend.middleware.DisableCsrfForApiMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'django_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # allow using the repo-level `frontend/` directory for templates (index.html)
        'DIRS': [BASE_DIR.parent / 'frontend'],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ]},
    },
]

_settings_pkg = __name__.rsplit('.', 1)[0]
# Derive a WSGI application path that matches how settings were imported.
# If settings live in a nested package (e.g. 'django_backend.django_backend.settings')
# this will point to 'django_backend.django_backend.wsgi.application'. Otherwise
# it will be 'django_backend.wsgi.application'. This avoids ModuleNotFoundError
# when running with different import layouts.
WSGI_APPLICATION = os.environ.get('DJANGO_WSGI_APPLICATION', f"{_settings_pkg}.wsgi.application")

# Database configuration - for local runs use sqlite. If dj_database_url is
# installed and a DATABASE_URL env var is provided, it will be used.
try:
    import dj_database_url  # optional helper
    DATABASES = {
        'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
    }
except Exception:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(BASE_DIR / 'db.sqlite3'),
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# During development also look for static assets in the repo-level frontend/ folder
# Add frontend dir to STATICFILES_DIRS only if it exists; prevents warnings in
# environments (Render) where the path does not exist.
FRONTEND_DIR = BASE_DIR.parent / 'frontend'
if FRONTEND_DIR.exists():
    # serve static assets from frontend/static so requests to /static/css/... match
    static_subdir = FRONTEND_DIR / 'static'
    if static_subdir.exists():
        STATICFILES_DIRS = [static_subdir]
    else:
        STATICFILES_DIRS = [FRONTEND_DIR]
else:
    STATICFILES_DIRS = []


# For local development don't force Whitenoise or manifest storage; keep defaults
# If you deploy to production and want whitenoise, set DJANGO_DEBUG to False and
# configure STATICFILES_STORAGE accordingly.
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    try:
        # enable whitenoise in non-debug runs if installed
        MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    except Exception:
        STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
