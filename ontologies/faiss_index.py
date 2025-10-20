import os
import json
import threading
from typing import List, Optional

from .models import Ontology

# Lazy-loaded heavy modules (import inside functions to avoid high memory usage at import time)
_lock = threading.Lock()
_model = None
_index = None
_id_map: List[int] = []

INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss.index')


def _import_sentence_transformer():
    # local import so Django/Gunicorn workers don't import heavy libs at process start
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer


def _import_faiss():
    import faiss

    return faiss


def get_model():
    """Return a cached SentenceTransformer model. Imported lazily."""
    global _model
    if _model is None:
        SentenceTransformer = _import_sentence_transformer()
        # load model; this can be slow & memory-heavy
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def build_index(force: bool = False):
    """Build or rebuild FAISS index from Ontology records.

    This function intentionally does lazy imports and runs under a lock to avoid
    concurrent rebuilds. It is safe to call from request handlers but may be
    expensive; consider calling from background task.
    """
    global _index, _id_map
    # lazy imports
    faiss = _import_faiss()
    import numpy as np  # local import

    with _lock:
        docs = Ontology.objects.all().order_by('id')
        texts = []
        ids = []
        for d in docs:
            txt = json.dumps(d.json, ensure_ascii=False)
            texts.append(txt)
            ids.append(int(d.id))

        if len(texts) == 0:
            _index = None
            _id_map = []
            return

        model = get_model()
        # encode in batches to reduce peak memory usage if needed
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        # normalize for inner product similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        _index = index
        _id_map = ids
        # persist index (best-effort; ignore failures)
        try:
            faiss.write_index(index, os.path.abspath(INDEX_PATH))
        except Exception:
            # don't crash the web process if disk write fails
            pass


def load_index():
    """Try to load persisted FAISS index from disk. Import lazily."""
    global _index, _id_map
    faiss = _import_faiss()
    if os.path.exists(os.path.abspath(INDEX_PATH)):
        try:
            _index = faiss.read_index(os.path.abspath(INDEX_PATH))
        except Exception:
            _index = None


def ensure_index(background: bool = True):
    """Ensure an index exists. If background=True, schedule a non-blocking rebuild
    when the index is missing. If background=False, perform a synchronous build.
    """
    global _index
    if _index is not None:
        return
    # try loading persisted index first
    load_index()
    if _index is not None:
        return
    if background:
        # schedule rebuild in a background thread to avoid blocking request workers
        t = threading.Thread(target=build_index, daemon=True)
        t.start()
    else:
        build_index()


def query_top_k(text: str, k: int = 5) -> List[dict]:
    """Query the FAISS index and return compact results.

    If the index is not built, attempt to load disk copy; if still missing,
    build synchronously (caller should avoid calling during startup).
    """
    global _index, _id_map
    faiss = _import_faiss()

    if _index is None:
        # try loading on disk first to avoid a costly rebuild
        load_index()
    if _index is None:
        # last resort: build index synchronously
        build_index()
    model = get_model()
    emb = model.encode([text], convert_to_numpy=True, show_progress_bar=False)
    try:
        faiss.normalize_L2(emb)
    except Exception:
        # normalization might fail for unexpected inputs; continue
        pass
    # ensure we have an index
    if _index is None:
        return []
    try:
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
