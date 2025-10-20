Render deployment checklist

1) Create a new Web Service on Render (Full-Stack or Backend).
2) Connect your GitHub repository and choose this repo.
3) Build Command: (optional) leave blank or use pip install -r django_backend/requirements.txt
4) Start Command: `gunicorn django_backend.wsgi --bind 0.0.0.0:$PORT --workers 3`
5) Environment variables (set in Render dashboard):
   - DJANGO_SECRET_KEY: your production secret key
   - DJANGO_DEBUG: False
   - DJANGO_ALLOWED_HOSTS: your-domain.com (or '*' for testing)
   - DATABASE_URL: optional (if omitted, SQLite will be used)

Notes:
- Static files: whitenoise is configured in `settings.py`. During build the `collectstatic` step will be executed automatically by Render if you set the build command to run migrations and collectstatic.
- If you use Postgres on Render, set `DATABASE_URL` to the postgres connection string.
- Excluded `Ontology-Generator/` from gitignore since it's hosted separately on HF Spaces.

Quick local steps:
- Build venv: python -m venv .venv; .\.venv\Scripts\activate
- Install: pip install -r django_backend/requirements.txt
- Migrate: python manage.py migrate
- Run dev: python manage.py runserver 0.0.0.0:8000
