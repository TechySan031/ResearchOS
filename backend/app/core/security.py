"""Authentication and authorization helpers.

Phase 6 will replace the mock user with JWT-based authentication.  Until then
every request is attributed to a deterministic "development" user so that the
rest of the codebase can depend on a consistent ``CurrentUser`` type.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from fastapi import Request


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Lightweight representation of the authenticated user.

    Attributes:
        id: Unique user identifier (UUID string).
        email: User email address.
        name: Display name.
    """

    id: str = field(default_factory=lambda: "00000000-0000-0000-0000-000000000000")
    email: str = "dev@researchos.local"
    name: str = "Development User"


# Pre-built mock user for the development phase.
_MOCK_USER = CurrentUser(
    id="00000000-0000-0000-0000-000000000000",
    email="dev@researchos.local",
    name="Development User",
)


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency that returns the current authenticated user.

    In this stub implementation, every request is attributed to a mock
    development user.  Phase 6 will validate a JWT bearer token from the
    ``Authorization`` header and return the corresponding ``CurrentUser``.

    Args:
        request: The incoming FastAPI ``Request`` (unused for now).

    Returns:
        A ``CurrentUser`` instance.
    """
    # TODO(phase-6): extract & validate JWT, look up user in DB
    return _MOCK_USER
