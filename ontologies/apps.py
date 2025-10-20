from django.apps import AppConfig

class OntologiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ontologies'

    def ready(self):
        # import signals so they register
        from . import signals  # noqa
