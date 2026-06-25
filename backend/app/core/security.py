"""Authentication, authorization, and password hashing.

Provides JWT token creation/validation, bcrypt password hashing, and
FastAPI dependency functions for extracting the current user and
enforcing role-based access control.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

# ── Password Hashing ─────────────────────────────────────────────────────────
# ── Password Hashing ─────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(plain: str) -> str:
    plain = str(plain)

    if len(plain.encode("utf-8")) > 72:
        raise ValueError(
            f"Password exceeds bcrypt limit: {len(plain.encode('utf-8'))} bytes"
        )

    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(str(plain), hashed)


   

# ── JWT Tokens ───────────────────────────────────────────────────────────────


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_expiration_minutes))
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create a signed JWT refresh token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_expiration_days)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.  Raises ``JWTError`` on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ── CurrentUser Dataclass ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Lightweight representation of the authenticated user.

    Attributes:
        id: Unique user identifier (UUID string).
        email: User email address.
        name: Display name.
        role: User role for RBAC.
    """

    id: str
    email: str
    name: str
    role: str = "researcher"


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials=Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency that extracts and validates the JWT bearer token.

    Returns the corresponding ``CurrentUser`` from the database.

    Args:
        request: The incoming FastAPI ``Request``.
        credentials: The HTTP bearer token.

    Returns:
        A ``CurrentUser`` instance.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")
    role: str = payload.get("role", "researcher")

    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists in DB
    from app.models.database import User, get_async_session

    async with get_async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
    )


# ── Role-Based Access Control ────────────────────────────────────────────────


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that enforces role membership.

    Usage::

        @router.get("/admin-only")
        async def admin_only(
            user: CurrentUser = Depends(require_role("admin")),
        ):
            ...
    """

    async def _check_role(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(allowed_roles)}",
            )
        return user

    return _check_role


# Convenience dependency aliases
require_admin = require_role("admin")
require_researcher = require_role("admin", "researcher")
require_viewer = require_role("admin", "researcher", "viewer")
