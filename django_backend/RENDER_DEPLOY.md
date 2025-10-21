Production deploy notes for Render

Recommended environment variables (set in Render dashboard):

- WEB_CONCURRENCY: 1          # number of gunicorn workers (start low)
- GUNICORN_TIMEOUT: 60       # worker timeout seconds
- GUNICORN_GRACE: 30         # graceful timeout
- GUNICORN_MAX_REQUESTS: 1000
- GUNICORN_MAX_REQUESTS_JITTER: 50
- DJANGO_DEBUG: False
- DJANGO_SECRET_KEY: <your secret>
- DATABASE_URL: <render postgres url> (or leave to default sqlite for simple setups)

Notes:
- This repo loads sentence-transformers and faiss lazily to avoid OOM at gunicorn worker startup.
- Rebuilding FAISS is scheduled in a background thread when new ontologies are saved; for large collections use a background worker (Celery) instead.
- Ensure your Render instance has enough RAM to host the embedding model and FAISS index. If memory is limited, consider running embeddings in a separate service and calling it via HTTP.

Quick deploy steps:
1. Commit and push changes to GitHub.
2. In Render, create a Web Service linked to your GitHub repo and set the required environment variables above.
3. Use the default start command from the Procfile. Monitor logs for worker restarts and memory issues.

Troubleshooting:
- If you still see worker timeouts or OOMs, increase instance memory size or reduce WEB_CONCURRENCY to 1.
- If you see long first-request latency, prebuild the index using the management command:

    python manage.py rebuild_faiss

This will run a synchronous rebuild (may require more RAM temporarily).
