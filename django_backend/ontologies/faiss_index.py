import os
import json
import threading
from .models import Ontology

_lock = threading.Lock()
_model = None
_index = None
_id_map = []

INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss.index')


def get_model():
    """Lazily import and return the SentenceTransformer model."""
    global _model
    if _model is None:
        try:
            # import when needed to avoid heavy import at module load
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            _model = None
    return _model


def _ensure_faiss():
    """Helper to import faiss and numpy lazily."""
    try:
        import faiss
        import numpy as np
        return faiss, np
    except Exception:
        return None, None


def build_index(force=False):
    """Build or rebuild the FAISS index from Ontology objects.

    This function imports heavy libs lazily and protects against failures so
    the web process startup won't crash if FAISS or the model is unavailable.
    """
    global _index, _id_map
    with _lock:
        docs = Ontology.objects.all().order_by('id')
        texts = []
        ids = []
        for d in docs:
            # stringify ontology to index
            txt = json.dumps(d.json or {}, ensure_ascii=False)
            texts.append(txt)
            ids.append(int(d.id))

        if len(texts) == 0:
            _index = None
            _id_map = []
            return

        model = get_model()
        faiss, np = _ensure_faiss()
        if model is None or faiss is None or np is None:
            # cannot build index in this environment
            _index = None
            _id_map = []
            return

        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        # normalize for inner product similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        _index = index
        _id_map = ids
        # persist index
        try:
            faiss.write_index(index, os.path.abspath(INDEX_PATH))
        except Exception:
            pass


def load_index():
    """Attempt to load a persisted FAISS index if available."""
    global _index, _id_map
    faiss, _ = _ensure_faiss()
    if faiss is None:
        return
    if os.path.exists(os.path.abspath(INDEX_PATH)):
        try:
            _index = faiss.read_index(os.path.abspath(INDEX_PATH))
        except Exception:
            _index = None


def query_top_k(text, k=5):
    """Query top-k matching Ontology records by semantic similarity.

    This function lazily ensures the index and model are available. If not,
    it falls back to returning empty results to avoid crashing the web worker.
    """
    global _index, _id_map
    faiss, np = _ensure_faiss()
    if _index is None:
        # try loading persisted index first
        load_index()
    if _index is None:
        # attempt build (may be expensive) — caller should control when to call
        try:
            build_index()
        except Exception:
            return []

    model = get_model()
    if model is None or faiss is None or _index is None:
        return []

    emb = model.encode([text], convert_to_numpy=True, show_progress_bar=False)
    try:
        faiss.normalize_L2(emb)
        D, I = _index.search(emb, k)
    except Exception:
        return []

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(_id_map):
            continue
        oid = _id_map[idx]
        try:
            obj = Ontology.objects.get(id=oid)
            results.append({'id': oid, 'score': float(score), 'ontology': obj.json})
        except Ontology.DoesNotExist:
            continue
    return results
