from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Ontology
from .faiss_index import build_index


@receiver(post_save, sender=Ontology)
def after_save_ontology(sender, instance, **kwargs):
    try:
        build_index()
    except Exception:
        pass


@receiver(post_delete, sender=Ontology)
def after_delete_ontology(sender, instance, **kwargs):
    try:
        build_index()
    except Exception:
        pass
