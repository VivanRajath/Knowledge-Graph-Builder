"""WSGI shim for deployments that expect the top-level package path
`django_backend.wsgi`.

This module forwards to the actual WSGI application located at
`django_backend.django_backend.wsgi` (the inner package). Adding this shim
makes `gunicorn django_backend.wsgi` work regardless of whether the
project is run from the repository root or inside the `django_backend`
subfolder.
"""
import os
import importlib

# Prefer the inner package WSGI app; fall back to trying to set the
# DJANGO_SETTINGS_MODULE to the inner settings module if needed.
try:
    module = importlib.import_module('django_backend.django_backend.wsgi')
except Exception:
    # If the inner package isn't importable, try to set DJANGO_SETTINGS_MODULE
    # to the inner settings and import the standard django get_wsgi_application
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_backend.django_backend.settings')
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
else:
    # Export the application object from the inner module
    application = getattr(module, 'application')
