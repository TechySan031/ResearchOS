"""SQLAlchemy 2.0 async database models and session factory.

Uses ``mapped_column()`` / ``Mapped[]`` style throughout.  The async engine
and session maker are created lazily so that configuration is picked up
from ``app.config.settings`` at runtime.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from app.config import settings

# ── Declarative Base ─────────────────────────────────────────────────────────


class Base(AsyncAttrs, DeclarativeBase):
    """Application-wide declarative base for all ORM models."""

    type_annotation_map = {
        dict[str, Any]: SQLiteJSON,
    }


# ── Mixins ───────────────────────────────────────────────────────────────────


def _uuid() -> str:
    return str(uuid.uuid4())


# ── User ─────────────────────────────────────────────────────────────────────


class UserModel(Base):
    """Registered platform user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    projects: Mapped[list["ProjectModel"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


# ── Project ──────────────────────────────────────────────────────────────────


class ProjectModel(Base):
    """A single research project/workflow."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created", index=True,
    )
    workflow_state: Mapped[Optional[dict[str, Any]]] = mapped_column(
        SQLiteJSON, nullable=True,
    )
    settings_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "settings", SQLiteJSON, nullable=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    owner: Mapped["UserModel"] = relationship(back_populates="projects")
    papers: Mapped[list["PaperModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    citations: Mapped[list["CitationModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    agent_logs: Mapped[list["AgentLogModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    sections: Mapped[list["DocumentSectionModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id!r} title={self.title!r}>"


# ── Paper ────────────────────────────────────────────────────────────────────


class PaperModel(Base):
    """A research paper discovered or uploaded during a workflow."""

    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[Optional[dict[str, Any]]] = mapped_column(
        SQLiteJSON, nullable=True,
    )
    doi: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, index=True,
    )
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", SQLiteJSON, nullable=True,
    )
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="papers")
    citations: Mapped[list["CitationModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paper id={self.id!r} doi={self.doi!r}>"


# ── Citation ─────────────────────────────────────────────────────────────────


class CitationModel(Base):
    """A citation reference within a generated document."""

    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True,
    )
    paper_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("papers.id"), nullable=True, index=True,
    )
    citation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    formatted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unverified",
    )
    verification_details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        SQLiteJSON, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="citations")
    paper: Mapped[Optional["PaperModel"]] = relationship(back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation id={self.id!r} key={self.citation_key!r}>"


# ── Agent Log ────────────────────────────────────────────────────────────────


class AgentLogModel(Base):
    """Audit log entry produced by an agent during workflow execution."""

    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        SQLiteJSON, nullable=True,
    )
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog id={self.id!r} agent={self.agent_name!r}>"


# ── Document Section ─────────────────────────────────────────────────────────


class DocumentSectionModel(Base):
    """A section of the generated research document."""

    __tablename__ = "document_sections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="body",
    )
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="sections")

    def __repr__(self) -> str:
        return f"<DocumentSection id={self.id!r} title={self.title!r}>"


# ── Engine & Session Factory ─────────────────────────────────────────────────

_engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    future=True,
)

async_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and ensure it is closed afterwards.

    Usage::

        async with get_async_session() as session:
            result = await session.execute(...)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables that do not yet exist.

    Intended to be called once during application startup.  For production
    migrations, use Alembic instead.
    """
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Convenience aliases ──────────────────────────────────────────────────────
# Short names so services can use `from app.models.database import Project`

Project = ProjectModel
Paper = PaperModel
User = UserModel
Citation = CitationModel
AgentLog = AgentLogModel
DocumentSection = DocumentSectionModel
