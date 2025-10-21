from django.apps import AppConfig
from pathlib import Path


class OntologiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Use the full import path for the app to avoid a namespace package
    # conflict with a repository-level `ontologies` package.
    name = 'django_backend.ontologies'

    # Provide an explicit filesystem path so Django doesn't confuse this
    # app with the top-level `ontologies` package that exists elsewhere in
    # the repository.
    path = str(Path(__file__).resolve().parent)

    def ready(self):
        # import signals so they register
        from . import signals  # noqa
