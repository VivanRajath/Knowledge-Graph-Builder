import os
import requests
from typing import List, Optional

# Primary env var to point to a remote index service. If not set, default to
# the deployed Hugging Face Space that hosts the Query-chat service.
REMOTE_INDEX_URL = os.environ.get('REMOTE_INDEX_URL') or 'https://huggingface.co/spaces/VivanRajath/Query-chat'

# Optional helper env vars for Hugging Face Space auto-detection
HF_SPACE_USER = os.environ.get('HF_SPACE_USER')
HF_SPACE_NAME = os.environ.get('HF_SPACE_NAME')

# cache resolved base URL to avoid repeated probes
_RESOLVED_BASE: Optional[str] = None


def _candidates_from_hf(user: str, name: str) -> List[str]:
    """Return candidate base URLs for a Hugging Face Space deployment."""
    cand = []
    # Common HF Space hostnames (try variants)
    cand.append(f"https://{name}-{user}.hf.space")
    cand.append(f"https://{user}--{name}.hf.space")
    cand.append(f"https://{user}-{name}.hf.space")
    # Public UI URL (some spaces may accept POSTs directly under this domain)
    cand.append(f"https://huggingface.co/spaces/{user}/{name}")
    return cand


def _resolve_base(timeout: int = 2) -> Optional[str]:
    """Resolve a working remote index base URL by checking REMOTE_INDEX_URL or HF_SPACE_* vars.

    The function probes candidate base URLs for /status (GET) or /query (POST) to
    discover a reachable API. Returns the first working base URL or None.
    """
    global _RESOLVED_BASE
    if _RESOLVED_BASE:
        return _RESOLVED_BASE

    candidates = []
    if REMOTE_INDEX_URL:
        candidates.append(REMOTE_INDEX_URL.rstrip('/'))

    if HF_SPACE_USER and HF_SPACE_NAME:
        candidates.extend(_candidates_from_hf(HF_SPACE_USER, HF_SPACE_NAME))

    # quick probe: check /status then /query
    for base in candidates:
        try:
            # try status endpoint
            url = f"{base.rstrip('/')}/status"
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                _RESOLVED_BASE = base
                return base
        except Exception:
            pass
        try:
            # try query endpoint with a tiny test
            url = f"{base.rstrip('/')}/query"
            r = requests.post(url, json={'q': '__ping__', 'k': 1}, timeout=timeout)
            if r.status_code == 200:
                _RESOLVED_BASE = base
                return base
        except Exception:
            pass
    return None


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def query(text: str, k: int = 5, timeout: int = 5) -> List[dict]:
    """Query the remote index service and return list of results.

    Expected remote response: JSON list of {id, score, ontology}
    """
    base = _resolve_base()
    if not base:
        return []
    try:
        resp = requests.post(_url(base, '/query'), json={'q': text, 'k': k}, timeout=timeout)
        resp.raise_for_status()
        return resp.json() or []
    except Exception:
        return []


def status(timeout: int = 3) -> dict:
    """Return remote index status or empty dict on failure."""
    base = _resolve_base()
    if not base:
        return {}
    try:
        resp = requests.get(_url(base, '/status'), timeout=timeout)
        resp.raise_for_status()
        return resp.json() or {}
    except Exception:
        return {}


def ingest(docs: List[dict], timeout: int = 10) -> dict:
    """POST documents to the remote index service /ingest endpoint.

    docs: list of {'id': <int>, 'ontology': <dict>} as expected by Query-chat.
    Returns parsed JSON on success or empty dict on failure.
    """
    base = _resolve_base()
    if not base:
        return {}
    try:
        resp = requests.post(_url(base, '/ingest'), json=docs, timeout=timeout)
        resp.raise_for_status()
        return resp.json() or {}
    except Exception:
        return {}


def build_remote(timeout: int = 60) -> dict:
    """Trigger remote index build via /build endpoint.

    Returns parsed JSON on success or empty dict on failure.
    """
    base = _resolve_base()
    if not base:
        return {}
    try:
        resp = requests.post(_url(base, '/build'), timeout=timeout)
        resp.raise_for_status()
        return resp.json() or {}
    except Exception:
        return {}

