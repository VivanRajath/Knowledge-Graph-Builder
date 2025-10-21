Django backend for ontology storage and API

Usage (development):
  - Create and activate a virtualenv
  - Install: python -m pip install -r requirements.txt
  - Run migrations: python manage.py migrate
  - Start server: python manage.py runserver 0.0.0.0:8000

Production / Render notes:
  - Whitenoise is configured to serve static files.
  - Use the provided `Procfile` at the repository root for Render: `web: gunicorn django_backend.wsgi --bind 0.0.0.0:$PORT --workers 3`
  - Set environment variables in Render: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` and optionally `DATABASE_URL`.
  - Recommended build command on Render: `pip install -r django_backend/requirements.txt && python django_backend/manage.py migrate --noinput && python django_backend/manage.py collectstatic --noinput`

