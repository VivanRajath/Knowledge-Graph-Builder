from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Ontology
from .serializers import OntologySerializer
from .faiss_index import build_index, load_index
import re
from typing import List, Tuple

# --- Lightweight local semantic helpers (dependency-free) ---
_token_re = re.compile(r"\w+", re.UNICODE)

def _tokens(text: str):
    return _token_re.findall((text or '').lower())

def _collect_text(obj, depth: int = 0) -> List[Tuple[str, float]]:
    texts: List[Tuple[str, float]] = []
    if obj is None:
        return texts
    if isinstance(obj, str):
        texts.append((obj, max(1.0, 3.0 - depth * 0.3)))
        return texts
    if isinstance(obj, (int, float, bool)):
        texts.append((str(obj), 1.0))
        return texts
    if isinstance(obj, list):
        for item in obj:
            texts.extend(_collect_text(item, depth + 1))
        return texts
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_low = str(k).lower()
            key_weight = 1.0
            if any(x in key_low for x in ('label', 'name', 'title', 'desc', 'summary')):
                key_weight = 2.5
            if isinstance(v, (str, int, float, bool)):
                texts.append((str(v), key_weight))
            else:
                for t, w in _collect_text(v, depth + 1):
                    texts.append((t, w * key_weight))
        return texts
    try:
        s = str(obj)
        texts.append((s, 1.0))
    except Exception:
        pass
    return texts

def _score_query_against_doc(query: str, doc_obj: dict) -> float:
    q_tokens = set(_tokens(query))
    if not q_tokens:
        return 0.0
    collected = _collect_text(doc_obj)
    if not collected:
        return 0.0
    token_weights = {}
    for text, weight in collected:
        for t in _tokens(text):
            token_weights[t] = token_weights.get(t, 0.0) + float(weight)
    if not token_weights:
        return 0.0
    intersect = 0.0
    doc_sum = 0.0
    for t, w in token_weights.items():
        doc_sum += w
        if t in q_tokens:
            intersect += w
    if doc_sum <= 0:
        return 0.0
    score = intersect / (doc_sum + len(q_tokens))
    return float(score)

def query_top_k_local(text: str, k: int = 5):
    results = []
    from .models import Ontology
    for o in Ontology.objects.all():
        ont = o.json or {}
        s = _score_query_against_doc(text, ont)
        if s > 0:
            results.append({'id': o.id, 'score': float(s), 'ontology': ont})
    results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    return results[:k]

# --- end helpers ---
import os
import networkx as nx
from collections import deque
import requests
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import threading


class OntologyViewSet(viewsets.ModelViewSet):
    """Standard CRUD viewset with a create override to accept the
    frontend payload format. Frontend sends { filename, source, ontology }
    so we map `ontology` -> `json` before saving.
    """
    queryset = Ontology.objects.all().order_by('-created_at')
    serializer_class = OntologySerializer

    def create(self, request, *args, **kwargs):
        payload = request.data.copy()
       
        if 'ontology' in payload:
            payload['json'] = payload.pop('ontology')
   
        if 'json' in payload and not isinstance(payload['json'], str):
       
            pass
        try:
            serializer = self.get_serializer(data=payload)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as exc:
      
            return Response({'detail': 'Failed to save ontology', 'error': str(exc), 'payload_preview': str(payload)[:200]}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET','HEAD'])
def aggregated_graph(request):

    node_map = {}  # id -> node object
    relation_set = set()  # set of tuples (source, target, relation)
    relations = []

    def normalize_node(n):
 
        if isinstance(n, str):
            return {'id': n, 'label': n, 'type': 'Entity'}
        if isinstance(n, dict):
            nid = n.get('id') or n.get('label') or n.get('name')
            label = n.get('label') or n.get('name') or nid
            ntype = n.get('type') or n.get('class') or n.get('label') or 'Entity'
            return {'id': nid, 'label': label, 'type': ntype}
        return None

    def normalize_relation(r):
        if not r:
            return None
        if isinstance(r, dict):
            s = r.get('source') or r.get('from') or r.get('s')
            t = r.get('target') or r.get('to') or r.get('t')
            rel = r.get('relation') or r.get('label') or r.get('type') or 'related_to'
            return {'source': s, 'target': t, 'relation': rel}
        return None

    for o in Ontology.objects.all():
        data = o.json or {}
        nodes = data.get('nodes') or data.get('entities') or []
        rels = data.get('relations') or data.get('edges') or []

        for n in nodes:
            nn = normalize_node(n)
            if not nn or not nn.get('id'):
                continue
            nid = nn['id']
            if nid not in node_map:
                node_map[nid] = nn

        for r in rels:
            rr = normalize_relation(r)
            if not rr or not rr.get('source') or not rr.get('target'):
                continue
            key = (rr['source'], rr['target'], rr['relation'])
            if key in relation_set:
                continue
            relation_set.add(key)
            relations.append(rr)

    nodes_out = list(node_map.values())
    return Response({'nodes': nodes_out, 'relations': relations})


@api_view(['GET','HEAD'])
def search_graph(request):

    q = request.GET.get('q', '')
    k = int(request.GET.get('k', 5))
    if not q:
        # fallback to aggregated
        return aggregated_graph(request)

    # try to load existing index; building is expensive so only build when enabled
    try:
        load_index()
    except Exception:
        pass
    if os.environ.get('DJANGO_BUILD_FAISS', 'false').lower() in ('1','true','yes'):
        try:
            build_index()
        except Exception:
            pass

    results = query_top_k_local(q, k=k)

    # merge nodes/relations from results
    node_map = {}
    relations = []
    relation_set = set()

    def normalize_node(n):
        if isinstance(n, str):
            return {'id': n, 'label': n, 'type': 'Entity'}
        if isinstance(n, dict):
            nid = n.get('id') or n.get('label') or n.get('name')
            label = n.get('label') or n.get('name') or nid
            ntype = n.get('type') or n.get('class') or 'Entity'
            return {'id': nid, 'label': label, 'type': ntype}
        return None

    def normalize_relation(r):
        if not r:
            return None
        if isinstance(r, dict):
            s = r.get('source') or r.get('from')
            t = r.get('target') or r.get('to')
            rel = r.get('relation') or r.get('label') or 'related_to'
            return {'source': s, 'target': t, 'relation': rel}
        return None

    # Collect matched node ids per hit (simple substring match on id/label) to avoid sending full ontology JSON
    hit_snippets = []
    for hit in results:
        ont = hit.get('ontology') or {}
        nodes = ont.get('nodes') or ont.get('entities') or []
        rels = ont.get('relations') or ont.get('edges') or []

        # normalize and merge into global node map/relations
        for n in nodes:
            nn = normalize_node(n)
            if not nn or not nn.get('id'):
                continue
            nid = nn['id']
            if nid not in node_map:
                node_map[nid] = nn

        for r in rels:
            rr = normalize_relation(r)
            if not rr or not rr.get('source') or not rr.get('target'):
                continue
            key = (rr['source'], rr['target'], rr['relation'])
            if key in relation_set:
                continue
            relation_set.add(key)
            relations.append(rr)

        # find matched nodes inside this ontology using query substring (cheap heuristic)
        qlow = q.strip().lower()
        matched_ids = []
        if qlow:
            for n in nodes:
                nid = None
                label = None
                if isinstance(n, dict):
                    nid = (n.get('id') or '')
                    label = (n.get('label') or '')
                else:
                    nid = str(n)
                    label = str(n)
                if qlow in str(nid).lower() or qlow in str(label).lower():
                    matched_ids.append(nid)

        # create a compact snippet for this hit (ids + relations among matched nodes)
        snippet_nodes = []
        snippet_relations = []
        if matched_ids:
            mid_set = set(matched_ids)
            for n in nodes:
                nid = n.get('id') if isinstance(n, dict) else n
                if nid in mid_set:
                    nn = normalize_node(n)
                    if nn:
                        snippet_nodes.append(nn)
            for r in rels:
                rr = normalize_relation(r)
                if rr and rr.get('source') in mid_set and rr.get('target') in mid_set:
                    snippet_relations.append(rr)

        hit_snippets.append({'id': hit.get('id'), 'score': hit.get('score'), 'matched_ids': matched_ids, 'snippet': {'nodes': snippet_nodes, 'relations': snippet_relations}})

    # Build graph for traversal (use node ids and directed edges)
    G = nx.DiGraph()
    for n in node_map.values():
        G.add_node(n['id'], label=n.get('label'), type=n.get('type'))
    for r in relations:
        # only add edges where both nodes exist in node_map
        if r['source'] in node_map and r['target'] in node_map:
            G.add_edge(r['source'], r['target'], relation=r.get('relation'))

    # Determine seed node ids from semantic hits: prefer node ids found by substring match in hit_snippets
    seed_ids = set()
    for hs in hit_snippets:
        for mid in hs.get('matched_ids', []):
            if mid:
                seed_ids.add(mid)
    # fallback: if there were no per-node matches, use document ids as seeds
    if not seed_ids:
        for hit in results:
            if hit.get('id'):
                seed_ids.add(str(hit.get('id')))

    # hops param controls graph traversal depth (default 1)
    try:
        hops = int(request.GET.get('hops', 1))
    except Exception:
        hops = 1

    # BFS from seed nodes to collect neighbors up to `hops`
    traversed_nodes = set()
    traversed_edges = set()
    if G.number_of_nodes() > 0 and seed_ids:
        q = deque()
        for s in seed_ids:
            if s in G:
                q.append((s, 0))
                traversed_nodes.add(s)
        while q:
            node_id, depth = q.popleft()
            if depth >= hops:
                continue
            for nbr in G.successors(node_id):
                traversed_nodes.add(nbr)
                traversed_edges.add((node_id, nbr, G.edges[node_id, nbr].get('relation')))
                q.append((nbr, depth + 1))
            for nbr in G.predecessors(node_id):
                traversed_nodes.add(nbr)
                traversed_edges.add((nbr, node_id, G.edges[nbr, node_id].get('relation')))
                q.append((nbr, depth + 1))

    # assemble final nodes/relations: include both semantic-match merged content and traversal expansions
    # mark nodes that were seeds/matched for frontend highlighting
    final_node_map = {}
    for nid, node in node_map.items():
        include = (not traversed_nodes) or (nid in traversed_nodes)
        if include:
            node_copy = dict(node)
            node_copy['highlight'] = (nid in seed_ids)
            final_node_map[nid] = node_copy
    final_relations = []
    # include original relations that match traversed edges or initial merge
    if traversed_edges:
        for s, t, rel in traversed_edges:
            final_relations.append({'source': s, 'target': t, 'relation': rel})
    else:
        final_relations = relations

    # return compact matches/snippets rather than full ontology payloads
    return Response({'nodes': list(final_node_map.values()), 'relations': final_relations, 'matches': hit_snippets, 'traversal': {'seeds': list(seed_ids), 'hops': hops}})



@api_view(['POST'])
@csrf_exempt
def upload_document(request):
    """Accept file uploads from the frontend, forward them to the
    external Ontology-Generator HF Space, save returned ontology JSON
    into the Ontology model, and return the saved record.
    """
    f = request.FILES.get('file')
    if not f:
        return Response({'detail': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    hf_url = getattr(settings, 'HF_ONTOLOGY_GENERATOR_URL', 'https://huggingface.co/spaces/VivanRajath/Ontology-Generator')
    candidates = [
        hf_url.rstrip('/') + '/generate',
        hf_url.rstrip('/') + '/api/generate',
        hf_url.rstrip('/'),
    ]

    resp_json = None
    for url in candidates:
        try:
            files = {'file': (f.name, f.read())}
            r = requests.post(url, files=files, timeout=30)
            if r.status_code == 200:
                try:
                    resp_json = r.json()
                except Exception:
                    resp_json = {'ontology': r.text}
                break
        except Exception:
            continue

    if not resp_json:
        return Response({'detail': 'Failed to reach Ontology-Generator space'}, status=status.HTTP_502_BAD_GATEWAY)

    ont = resp_json.get('ontology') if isinstance(resp_json, dict) and 'ontology' in resp_json else resp_json

    try:
        o = Ontology.objects.create(filename=f.name, source='hf_space', json=ont)
        remote_result = {}
        try:
            from .remote_index import ingest as remote_ingest, build_remote
            try:
                ingest_resp = remote_ingest([{'id': o.id, 'ontology': ont}])
                remote_result['ingest'] = ingest_resp
            except Exception as e:
                remote_result['ingest_error'] = str(e)
            def _build():
                try:
                    b = build_remote()
                    if settings.DEBUG:
                        print('remote build response:', b)
                    remote_result['build'] = b
                except Exception as e:
                    remote_result['build_error'] = str(e)
            t = threading.Thread(target=_build, daemon=True)
            t.start()
        except Exception as e:
            remote_result['import_error'] = str(e)

        serializer = OntologySerializer(o)
        resp = serializer.data
        resp['_remote'] = remote_result
        return Response(resp, status=status.HTTP_201_CREATED)
    except Exception as exc:
        return Response({'detail': 'Failed to save ontology', 'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
def remote_query(request):
    """Proxy query requests from frontend to the configured remote index.

    Accepts JSON {query: str, k: int}
    """
    payload = request.data or {}
    q = payload.get('query') or payload.get('q') or ''
    k = int(payload.get('k') or 5)
    if not q:
        return Response({'detail': 'Missing query'}, status=status.HTTP_400_BAD_REQUEST)
    results = query_top_k_local(q, k=k)
    return Response({'results': results})
