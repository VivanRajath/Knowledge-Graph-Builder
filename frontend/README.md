Knowledge Graph Builder — Frontend

This is a lightweight Obsidian-style single-file SPA placed in `frontend/`.

What it contains
- `index.html` — the SPA shell.
- `static/css/style.css` — simple dark theme and layout.
- `static/js/app.js` — client-side graph UI (vis-network), file uploader (placeholder), chat/query placeholder.

How to run locally
1. From project root, start a simple static server (PowerShell):

```powershell
# Windows: use Python's http.server
cd frontend
python -m http.server 8000
# then open http://localhost:8000 in a browser
```

Integration notes
- Uploads POST to `/api/upload` and query/chat POST to `/api/query`. Hook these endpoints in your Django backend (e.g., add views in `ontologies.views`) to accept files and run indexing or to proxy to your chat/query service.
- For production, add `frontend/` to Django static files settings or build a proper frontend bundler pipeline.

Next steps
- Wire the `/api/upload` and `/api/query` endpoints.
- Add persistent saving of graphs (POST/GET to backend) and richer editor UI.
