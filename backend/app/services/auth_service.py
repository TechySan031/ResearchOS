"""Authentication service — register, login, refresh, and logout.

Encapsulates user lifecycle database operations and delegates token
creation to ``app.core.security``.
"""

from __future__ import annotations

import uuid
import datetime as _dt
from typing import Optional

from jose import JWTError
from sqlalchemy import select

from app.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.database import User, get_async_session
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service class for authentication operations."""

    @staticmethod
    async def register(
        email: str,
        password: str,
        name: str,
        role: str = "researcher",
    ) -> User:
        """Register a new user.

        Args:
            email: User email (lowercased).
            password: Plain-text password (will be hashed).
            name: Display name.
            role: User role (default: ``researcher``).

        Returns:
            The newly created ``User`` ORM instance.

        Raises:
            ValidationError: If the email is already registered.
        """
        email = email.lower().strip()

        async with get_async_session() as session:
            existing = await session.execute(
                select(User).where(User.email == email)
            )
            if existing.scalar_one_or_none() is not None:
                raise ValidationError(
                    "A user with this email already exists",
                    status_code=409,
                )

            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                hashed_password=hash_password(password),
                role=role,
                created_at=_dt.datetime.now(_dt.timezone.utc),
                updated_at=_dt.datetime.now(_dt.timezone.utc),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info("auth.user_registered", user_id=user.id, email=email)
            return user

    @staticmethod
    async def login(email: str, password: str) -> tuple[User, str, str]:
        """Authenticate a user and return tokens.

        Args:
            email: User email.
            password: Plain-text password.

        Returns:
            Tuple of (User, access_token, refresh_token).

        Raises:
            ValidationError: If credentials are invalid.
        """
        email = email.lower().strip()

        async with get_async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

        if user is None or user.hashed_password is None:
            raise ValidationError("Invalid email or password", status_code=401)

        if not verify_password(password, user.hashed_password):
            raise ValidationError("Invalid email or password", status_code=401)

        access_token = create_access_token(user.id, user.email, user.role)
        refresh_token = create_refresh_token(user.id)

        logger.info("auth.user_login", user_id=user.id, email=email)
        return user, access_token, refresh_token

    @staticmethod
    async def refresh(refresh_token_str: str) -> tuple[str, str]:
        """Validate a refresh token and issue new token pair.

        Args:
            refresh_token_str: The JWT refresh token.

        Returns:
            Tuple of (new_access_token, new_refresh_token).

        Raises:
            ValidationError: If the refresh token is invalid.
        """
        try:
            payload = decode_token(refresh_token_str)
        except JWTError:
            raise ValidationError("Invalid or expired refresh token", status_code=401)

        if payload.get("type") != "refresh":
            raise ValidationError("Invalid token type", status_code=401)

        user_id = payload.get("sub")
        if user_id is None:
            raise ValidationError("Malformed token", status_code=401)

        async with get_async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

        if user is None:
            raise ValidationError("User no longer exists", status_code=401)

        access_token = create_access_token(user.id, user.email, user.role)
        new_refresh_token = create_refresh_token(user.id)

        logger.info("auth.token_refreshed", user_id=user.id)
        return access_token, new_refresh_token

    @staticmethod
    async def get_user_by_id(user_id: str) -> User:
        """Retrieve a user by ID.

        Args:
            user_id: UUID of the user.

        Returns:
            The matching ``User``.

        Raises:
            NotFoundError: If no user with the given ID exists.
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise NotFoundError(f"User {user_id} not found")
            return user

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Retrieve a user by email address.

        Args:
            email: Email to look up (case-insensitive).

        Returns:
            The matching ``User`` or ``None``.
        """
        email = email.lower().strip()
        async with get_async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
