"""Pydantic v2 request / response schemas for the ResearchOS REST API.

Every schema uses ``model_config = ConfigDict(from_attributes=True)`` so
that ORM model instances can be serialised directly via
``SchemaClass.model_validate(orm_instance)``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ── Generic paginated container ──────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list endpoints.

    Attributes:
        items: Current page of results.
        total: Total number of matching records.
        page: Current page number (1-indexed).
        page_size: Maximum records per page.
        total_pages: Total number of pages.
    """

    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


# ── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response for the ``/health`` endpoint."""

    status: str = "ok"
    version: str
    environment: str
    database: str = "connected"
    redis: str = "connected"


# ── Project ──────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    """Payload to create a new research project."""

    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = Field(None, max_length=5000)
    topic: Optional[str] = Field(None, max_length=2000)
    user_id: str = Field(default="default-user")
    settings: Optional[dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """Payload to partially update an existing project."""

    title: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = Field(None, max_length=5000)
    topic: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """Serialised project for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None
    status: str
    workflow_state: Optional[dict[str, Any]] = None
    settings_json: Optional[dict[str, Any]] = Field(None, alias="settings")
    owner_id: str
    created_at: datetime
    updated_at: datetime


# ── Paper ────────────────────────────────────────────────────────────────────


class PaperSearchRequest(BaseModel):
    """Query parameters for searching academic papers."""

    query: str = Field(..., min_length=1, max_length=1000)
    sources: Optional[List[str]] = None
    max_results: int = Field(10, ge=1, le=100)
    year_from: Optional[int] = None
    year_to: Optional[int] = None


class PaperResponse(BaseModel):
    """Serialised paper record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    abstract: Optional[str] = None
    authors: Optional[dict[str, Any]] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: str
    year: Optional[int] = None
    metadata_json: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime


class PaperUploadResponse(BaseModel):
    """Response after uploading a PDF paper."""

    id: str
    title: str
    filename: str
    pages: int
    message: str = "Paper uploaded and queued for processing."


# ── Research / Workflow ──────────────────────────────────────────────────────


class ResearchStartRequest(BaseModel):
    """Payload to kick off the research workflow for a project."""

    project_id: str
    search_queries: Optional[List[str]] = None
    max_papers: int = Field(20, ge=1, le=200)
    format_style: str = Field("ieee", pattern=r"^(ieee|acm|springer)$")


class ResearchStatusResponse(BaseModel):
    """Current status of a running research workflow."""

    project_id: str
    status: str
    current_agent: Optional[str] = None
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ── Agent ────────────────────────────────────────────────────────────────────


class AgentStatusResponse(BaseModel):
    """Real-time status of a specific agent."""

    agent_name: str
    status: str
    message: Optional[str] = None
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)


class AgentLogResponse(BaseModel):
    """Serialised agent log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    agent_name: str
    event_type: str
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None
    created_at: datetime


# ── Citation ─────────────────────────────────────────────────────────────────


class CitationResponse(BaseModel):
    """Serialised citation record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    paper_id: Optional[str] = None
    citation_key: str
    formatted_text: Optional[str] = None
    status: str
    verification_details: Optional[dict[str, Any]] = None
    created_at: datetime


class CitationVerificationResponse(BaseModel):
    """Result of verifying a citation against external sources."""

    citation_id: str
    citation_key: str
    status: str
    doi_valid: Optional[bool] = None
    url_reachable: Optional[bool] = None
    details: Optional[dict[str, Any]] = None


# ── Document Section ─────────────────────────────────────────────────────────


class DocumentSectionResponse(BaseModel):
    """Serialised document section."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    content: Optional[str] = None
    section_order: int
    section_type: str
    word_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class DocumentUpdateRequest(BaseModel):
    """Payload to update a document section's content."""

    title: Optional[str] = Field(None, min_length=1, max_length=512)
    content: Optional[str] = None
    section_order: Optional[int] = None


# ── Export ───────────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    """Parameters for exporting the final document."""

    project_id: str
    format: str = Field("pdf", pattern=r"^(pdf|docx|markdown|latex)$")
    include_references: bool = True
    include_appendix: bool = False


class ExportResponse(BaseModel):
    """Download information for an exported document."""

    project_id: str
    format: str
    filename: str
    download_url: str
    size_bytes: int
    created_at: datetime


# ── WebSocket ────────────────────────────────────────────────────────────────


class WebSocketMessage(BaseModel):
    """Envelope for messages sent over WebSocket connections.

    Attributes:
        type: Message category (e.g. ``agent_event``, ``status_update``).
        project_id: Related project UUID.
        data: Arbitrary payload.
        timestamp: ISO-formatted timestamp string.
    """

    type: str
    project_id: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None
