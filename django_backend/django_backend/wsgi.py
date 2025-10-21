import os
from django.core.wsgi import get_wsgi_application

# Point to the fully-qualified settings module inside the inner package.
# This avoids ambiguity when the repository root also contains a
# top-level `django_backend` package.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_backend.django_backend.settings')
application = get_wsgi_application()
