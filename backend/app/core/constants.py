"""Application constants shared across the ResearchOS backend."""

from __future__ import annotations

from enum import StrEnum, unique


# ── Agent Names ──────────────────────────────────────────────────────────────

@unique
class AgentName(StrEnum):
    """Canonical names for every agent in the research pipeline."""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    SEARCH = "search"
    FETCH = "fetch"
    PARSER = "parser"
    ANALYZER = "analyzer"
    WRITER = "writer"
    EDITOR = "editor"
    CITATION = "citation"
    FORMAT = "format"
    QUALITY = "quality"
    ORCHESTRATOR = "orchestrator"


# ── Workflow Status ──────────────────────────────────────────────────────────

@unique
class WorkflowStatus(StrEnum):
    """High-level statuses a research workflow can be in."""

    CREATED = "created"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


# ── Paper Sources ────────────────────────────────────────────────────────────

@unique
class PaperSource(StrEnum):
    """Where a paper was originally discovered."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CROSSREF = "crossref"
    UPLOAD = "upload"


# ── Chunk / Embedding Constants ──────────────────────────────────────────────

DEFAULT_CHUNK_SIZE: int = 512
DEFAULT_CHUNK_OVERLAP: int = 64
MAX_CHUNK_SIZE: int = 1024
MAX_DOCUMENT_TOKENS: int = 128_000

# ── API Rate Limits (requests per minute per source) ─────────────────────────

RATE_LIMITS: dict[str, int] = {
    PaperSource.ARXIV: 30,
    PaperSource.SEMANTIC_SCHOLAR: 100,
    PaperSource.CROSSREF: 50,
}

# ── Retry Defaults ───────────────────────────────────────────────────────────

DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_FACTOR: float = 1.0

# ── Timeout Defaults (seconds) ────────────────────────────────────────────

LLM_GENERATION_TIMEOUT: float = 180.0  # LLM streaming/generation
VECTORSTORE_OPERATION_TIMEOUT: float = 15.0  # Pinecone indexing

# ── Event Types ──────────────────────────────────────────────────────────

EVENT_TYPE_TIMEOUT = "timeout"
EVENT_TYPE_DEGRADED = "degraded"

# ── Miscellaneous ────────────────────────────────────────────────────────────

CORRELATION_ID_HEADER: str = "X-Correlation-ID"
MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
SUPPORTED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset({".pdf"})
