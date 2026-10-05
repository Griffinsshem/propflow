"""gunicorn production settings.

Sizing is measured, not guessed: docs/performance/load-test-results.md, section 6.
"""

import os

# Render routes traffic to $PORT on the instance; nothing else can reach it.
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
# Sync workers, 2 per vCPU: requests spend ~35-45% of their time waiting on the database.
worker_class = "sync"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
# Each worker builds its own app and connection pool: no connections shared across fork.
preload_app = False
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
# Finish in-flight requests on deploys and scale-downs, inside Render's 30 s shutdown window.
graceful_timeout = 25
keepalive = 5
# Recycle workers periodically so slow memory growth can never accumulate.
max_requests = 2000
max_requests_jitter = 200
# The app logs one structured line per request (request ID, timings): no duplicate access log.
accesslog = None
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
