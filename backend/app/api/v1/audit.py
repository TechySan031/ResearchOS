"""Audit log API endpoints.

Provides read-only access to audit trail entries.  Restricted to admin
users only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.security import CurrentUser, require_admin
from app.models.schemas import AuditLogResponse
from app.services.audit_service import AuditService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["audit"])


@router.get(
    "",
    response_model=list[AuditLogResponse],
    summary="List audit log entries",
)
async def list_audit_logs(
    user_id: str | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    _admin: CurrentUser = Depends(require_admin),
) -> list[AuditLogResponse]:
    """List audit log entries with optional filters.

    Only accessible by admin users.

    Args:
        user_id: Optional user ID filter.
        action: Optional action filter.
        resource_type: Optional resource type filter.
        skip: Pagination offset.
        limit: Pagination page size.
    """
    logger.info(
        "api.audit.list",
        filter_user_id=user_id,
        filter_action=action,
    )

    logs = await AuditService.list_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        skip=skip,
        limit=limit,
    )
    return [
        AuditLogResponse.model_validate(entry, from_attributes=True)
        for entry in logs
    ]
