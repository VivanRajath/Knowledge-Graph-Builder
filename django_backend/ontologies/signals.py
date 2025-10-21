from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import threading
import time
from .models import Ontology
from . import faiss_index

# Debounce rebuilds: if multiple saves/deletes happen in quick succession,
# only perform one rebuild after the quiet period. This prevents thrashing
# the web worker at import/save time.
_debounce_lock = threading.Lock()
_debounce_timer = None
_DEBOUNCE_SECONDS = 2.0


def _schedule_rebuild():
    global _debounce_timer

    def _worker():
        # small sleep to collect additional events
        time.sleep(_DEBOUNCE_SECONDS)
        try:
            faiss_index.build_index()
        except Exception:
            # never let signal handlers raise
            pass

    with _debounce_lock:
        if _debounce_timer and _debounce_timer.is_alive():
            # already scheduled
            return
        _debounce_timer = threading.Thread(target=_worker, daemon=True)
        _debounce_timer.start()


@receiver(post_save, sender=Ontology)
def after_save_ontology(sender, instance, **kwargs):
    try:
        _schedule_rebuild()
    except Exception:
        pass


@receiver(post_delete, sender=Ontology)
def after_delete_ontology(sender, instance, **kwargs):
    try:
        _schedule_rebuild()
    except Exception:
        pass
