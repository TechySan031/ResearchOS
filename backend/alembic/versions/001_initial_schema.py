"""Initial schema – all six core tables.

Revision ID: 001
Revises: None
Create Date: 2026-05-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("hashed_password", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ── projects ─────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("workflow_state", sa.JSON(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_projects_owner_id_users")),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_projects_status"), "projects", ["status"])
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"])

    # ── papers ───────────────────────────────────────────────────────────
    op.create_table(
        "papers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", name=op.f("fk_papers_project_id_projects")),
            nullable=False,
        ),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_papers_project_id"), "papers", ["project_id"])
    op.create_index(op.f("ix_papers_doi"), "papers", ["doi"])

    # ── citations ────────────────────────────────────────────────────────
    op.create_table(
        "citations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey(
                "projects.id", name=op.f("fk_citations_project_id_projects")
            ),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            sa.String(36),
            sa.ForeignKey("papers.id", name=op.f("fk_citations_paper_id_papers")),
            nullable=True,
        ),
        sa.Column("citation_key", sa.String(128), nullable=False),
        sa.Column("formatted_text", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="unverified"
        ),
        sa.Column("verification_details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_citations_project_id"), "citations", ["project_id"])
    op.create_index(op.f("ix_citations_paper_id"), "citations", ["paper_id"])

    # ── agent_logs ───────────────────────────────────────────────────────
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey(
                "projects.id", name=op.f("fk_agent_logs_project_id_projects")
            ),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_agent_logs_project_id"), "agent_logs", ["project_id"])
    op.create_index(op.f("ix_agent_logs_agent_name"), "agent_logs", ["agent_name"])

    # ── document_sections ────────────────────────────────────────────────
    op.create_table(
        "document_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey(
                "projects.id",
                name=op.f("fk_document_sections_project_id_projects"),
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "section_type", sa.String(64), nullable=False, server_default="body"
        ),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_document_sections_project_id"),
        "document_sections",
        ["project_id"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(
        op.f("ix_document_sections_project_id"), table_name="document_sections"
    )
    op.drop_table("document_sections")

    op.drop_index(op.f("ix_agent_logs_agent_name"), table_name="agent_logs")
    op.drop_index(op.f("ix_agent_logs_project_id"), table_name="agent_logs")
    op.drop_table("agent_logs")

    op.drop_index(op.f("ix_citations_paper_id"), table_name="citations")
    op.drop_index(op.f("ix_citations_project_id"), table_name="citations")
    op.drop_table("citations")

    op.drop_index(op.f("ix_papers_doi"), table_name="papers")
    op.drop_index(op.f("ix_papers_project_id"), table_name="papers")
    op.drop_table("papers")

    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
