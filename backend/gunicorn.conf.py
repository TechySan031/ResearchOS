"""
ResearchOS — Gunicorn Production Configuration

Optimised for a FastAPI application served behind a reverse proxy.
Uses UvicornWorker for async request handling.
"""

import os

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
port = os.getenv("PORT", "8000")
bind = f"0.0.0.0:{port}"

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------

workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# ---------------------------------------------------------------------------
# Timeouts  (generous for LLM / RAG streaming calls)
# ---------------------------------------------------------------------------
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30           # seconds to finish in-flight requests on SIGTERM
keepalive = 5                   # seconds to wait for next request on a Keep-Alive connection

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = "-"                 # stdout
errorlog = "-"                  # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'
)

# ---------------------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------------------
proc_name = "researchos-api"

# ---------------------------------------------------------------------------
# Server mechanics
# ---------------------------------------------------------------------------
preload_app = False             # avoid shared state across workers
max_requests = 1000             # restart a worker after N requests (leak guard)
max_requests_jitter = 50        # randomise restarts to avoid thundering herd

# ---------------------------------------------------------------------------
# Forwarded headers (trust reverse-proxy X-Forwarded-* headers)
# ---------------------------------------------------------------------------
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")
proxy_protocol = False
