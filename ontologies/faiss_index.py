import os
import json
import threading
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

from .models import Ontology

_lock = threading.Lock()
_model = None
_index = None
_id_map = []

INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss.index')

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def build_index(force=False):
    global _index, _id_map
    with _lock:
        docs = Ontology.objects.all().order_by('id')
        texts = []
        ids = []
        for d in docs:
            # stringify ontology to index
            txt = json.dumps(d.json, ensure_ascii=False)
            texts.append(txt)
            ids.append(int(d.id))

        if len(texts) == 0:
            _index = None
            _id_map = []
            return

        model = get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        # normalize for inner product similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        _index = index
        _id_map = ids
        # persist index
        faiss.write_index(index, os.path.abspath(INDEX_PATH))

def load_index():
    global _index, _id_map
    if os.path.exists(os.path.abspath(INDEX_PATH)):
        _index = faiss.read_index(os.path.abspath(INDEX_PATH))
        # we do not persist id_map currently — rebuild index if needed

def query_top_k(text, k=5):
    global _index, _id_map
    if _index is None:
        build_index()
    model = get_model()
    emb = model.encode([text], convert_to_numpy=True, show_progress_bar=False)
    faiss.normalize_L2(emb)
    D, I = _index.search(emb, k)
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
