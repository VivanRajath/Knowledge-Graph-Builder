import os
import json
import threading
from typing import List, Optional

from .models import Ontology

# This module intentionally avoids importing FAISS or heavy ML libraries.
# Instead the codebase delegates queries to a remote index service (HF Space).
from .remote_index import query as remote_query, REMOTE_INDEX_URL


def build_index(force: bool = False):
    """No-op in web app: index is managed remotely in the HF Space.

    Keep a compatible function signature for management commands and signals
    but don't attempt to build a local FAISS index in the web process.
    """
    return


def load_index():
    """No-op: index is remote."""
    return


def ensure_index(background: bool = True):
    """No-op: the remote service manages index builds."""
    return


def query_top_k(text: str, k: int = 5) -> List[dict]:
    """Delegate queries to the configured remote index service.

    Returns an empty list if the remote service is unreachable.
    """
    try:
        return remote_query(text, k=k)
    except Exception:
        return []
