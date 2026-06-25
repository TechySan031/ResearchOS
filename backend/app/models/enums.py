"""Shared enumerations used by database models, schemas, and business logic."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class UserRole(StrEnum):
    """Roles for RBAC."""

    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


@unique
class AuditAction(StrEnum):
    """Actions recorded in the audit log."""

    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TOKEN_REFRESHED = "token_refreshed"
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    EXPORT_REQUESTED = "export_requested"
    COPILOT_CHAT = "copilot_chat"


@unique
class WorkflowStatus(StrEnum):
    """High-level statuses a research workflow can transition through."""

    CREATED = "created"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


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


@unique
class PaperSource(StrEnum):
    """Origin of a paper record."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CROSSREF = "crossref"
    UPLOAD = "upload"


@unique
class CitationStatus(StrEnum):
    """Verification state of a citation link."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


@unique
class FormatStyle(StrEnum):
    """Supported bibliography formatting standards."""

    IEEE = "ieee"
    ACM = "acm"
    SPRINGER = "springer"


@unique
class AgentEventType(StrEnum):
    """Lifecycle phases that agents report."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"
