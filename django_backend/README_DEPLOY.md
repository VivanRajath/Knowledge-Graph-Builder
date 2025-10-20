Deploying to Render (quick guide)

1. Push your repo to GitHub.
2. In Render, create a new Web Service and connect your GitHub repository.
3. Set the build command (optional):
   pip install -r django_backend/requirements.txt
4. Set the start command (Render):
   gunicorn django_backend.wsgi --bind 0.0.0.0:$PORT --workers 3
5. Set environment variables in Render:
   - DJANGO_SECRET_KEY (required)
   - DJANGO_DEBUG=false
   - DJANGO_ALLOWED_HOSTS=yourdomain.com
   - DATABASE_URL (optional) — if set, use a Render Postgres database

Local test commands (PowerShell):

# create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install
pip install -r django_backend/requirements.txt

# migrate
python django_backend/manage.py migrate

# collect static (optional for local test)
python django_backend/manage.py collectstatic --noinput

# run
python django_backend/manage.py runserver
