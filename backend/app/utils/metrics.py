"""Prometheus metrics for the ResearchOS backend.

All metrics are defined here as module-level singletons so that every part
of the application can import and update them without worrying about double
registration.

Call ``setup_metrics()`` during startup if any one-time configuration is
needed (currently a no-op, kept for forward compatibility).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Request Metrics ──────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "researchos_http_requests_total",
    "Total number of HTTP requests.",
    labelnames=["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "researchos_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Agent Metrics ────────────────────────────────────────────────────────────

AGENT_DURATION = Histogram(
    "researchos_agent_duration_seconds",
    "Wall-clock time an agent spends processing a task.",
    labelnames=["agent_name"],
    buckets=(0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# ── Token Usage ──────────────────────────────────────────────────────────────

TOKENS_USED = Counter(
    "researchos_llm_tokens_total",
    "Total LLM tokens consumed.",
    labelnames=["model"],
)

# ── Workflow Metrics ─────────────────────────────────────────────────────────

ACTIVE_WORKFLOWS = Gauge(
    "researchos_active_workflows",
    "Number of research workflows currently in progress.",
)


def setup_metrics() -> None:
    """Perform any one-time metrics initialisation.

    Currently a no-op — metrics are lazily created at import time by
    prometheus_client.  This function exists so that the startup sequence
    has an explicit hook for future work (e.g. custom collectors or push
    gateway configuration).
    """
    # Intentionally empty — metrics are auto-registered on first import.
