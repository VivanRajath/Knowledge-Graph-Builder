from typing import List

"""Lightweight FAISS delegator for the Django backend package.

This module avoids importing FAISS or heavy ML libraries in the web process.
It forwards semantic-search queries to the configured remote index service
(for example the Hugging Face Space) via the `ontologies.remote_index` helper.
"""

try:
    # Use absolute import to ensure the linter and runtime can resolve the module
    from .remote_index import query as remote_query, REMOTE_INDEX_URL
except Exception:
    # Fallback: provide a dummy delegator if import fails (keeps API stable)
    remote_query = None
    REMOTE_INDEX_URL = None


def build_index(force: bool = False):
    """No-op: index is managed remotely."""
    return


def load_index():
    """No-op: index is remote."""
    return


def query_top_k(text: str, k: int = 5) -> List[dict]:
    """Delegate queries to the remote index service.

    Returns an empty list if the remote service is unavailable.
    """
    if remote_query is None:
        return []
    try:
        return remote_query(text, k=k)
    except Exception:
        return []
