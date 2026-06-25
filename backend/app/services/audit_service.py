"""Audit logging service.

Records immutable audit trail entries for authentication, workflow,
export, and copilot events.  All methods are async and manage their own
database sessions via ``get_async_session()``.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Optional, Sequence

from sqlalchemy import select

from app.models.database import AuditLog, get_async_session
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service class for audit log operations."""

    @staticmethod
    async def log(
        action: str,
        *,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            action: The audit action string (e.g. ``user_login``).
            user_id: UUID of the acting user (if known).
            resource_type: Type of the affected resource (e.g. ``project``).
            resource_id: UUID of the affected resource.
            detail: Human-readable detail string.
            ip_address: Client IP address.
            user_agent: Client user-agent header.

        Returns:
            The newly created ``AuditLog`` ORM instance.
        """
        async with get_async_session() as session:
            entry = AuditLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=_dt.datetime.now(_dt.timezone.utc),
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)

            logger.info(
                "audit.logged",
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            return entry

    @staticmethod
    async def list_logs(
        *,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """List audit log entries with optional filters.

        Args:
            user_id: Filter by acting user.
            action: Filter by action type.
            resource_type: Filter by resource type.
            skip: Pagination offset.
            limit: Pagination page size.

        Returns:
            A list of ``AuditLog`` instances.
        """
        async with get_async_session() as session:
            stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
            if user_id is not None:
                stmt = stmt.where(AuditLog.user_id == user_id)
            if action is not None:
                stmt = stmt.where(AuditLog.action == action)
            if resource_type is not None:
                stmt = stmt.where(AuditLog.resource_type == resource_type)
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())
