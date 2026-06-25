"""Custom exception hierarchy for the ResearchOS platform.

Every domain exception inherits from ``ResearchOSError`` so that the global
error-handler middleware can recognise and serialize them uniformly.
"""

from __future__ import annotations

from typing import Any


class ResearchOSError(Exception):
    """Base exception for all ResearchOS domain errors.

    Attributes:
        status_code: Suggested HTTP status code for the response.
        detail: Human-readable error description.
        context: Optional dict of structured data for debugging.
    """

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        *,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        if status_code is not None:
            self.status_code = status_code
        self.context: dict[str, Any] = context or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error for JSON responses."""
        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "detail": self.detail,
        }
        if self.context:
            payload["context"] = self.context
        return payload


class NotFoundError(ResearchOSError):
    """Raised when a requested resource does not exist."""

    status_code: int = 404
    detail: str = "The requested resource was not found."


class ValidationError(ResearchOSError):
    """Raised when user input fails domain-level validation."""

    status_code: int = 422
    detail: str = "Validation failed."


class ExternalAPIError(ResearchOSError):
    """Raised when an external service call fails."""

    status_code: int = 502
    detail: str = "An external API request failed."

    def __init__(
        self,
        detail: str | None = None,
        *,
        service: str | None = None,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        context = context or {}
        if service is not None:
            context["service"] = service
        super().__init__(detail, status_code=status_code, context=context)


class RateLimitError(ResearchOSError):
    """Raised when a rate limit is exceeded (local or upstream)."""

    status_code: int = 429
    detail: str = "Rate limit exceeded. Please try again later."


class EmbeddingError(ResearchOSError):
    """Raised when vector embedding generation or retrieval fails."""

    status_code: int = 500
    detail: str = "Embedding operation failed."


class VectorStoreError(ResearchOSError):
    """Raised when the vector store (Pinecone) interaction fails."""

    status_code: int = 500
    detail: str = "Vector store operation failed."


class AgentError(ResearchOSError):
    """Raised when an LLM agent encounters an unrecoverable error."""

    status_code: int = 500
    detail: str = "Agent execution failed."


class WorkflowError(ResearchOSError):
    """Raised when the overall research workflow reaches an invalid state."""

    status_code: int = 500
    detail: str = "Workflow execution failed."


class AuthenticationError(ResearchOSError):
    """Raised when authentication fails (bad credentials, expired token)."""

    status_code: int = 401
    detail: str = "Authentication failed."


class AuthorizationError(ResearchOSError):
    """Raised when the user lacks permissions for an operation."""

    status_code: int = 403
    detail: str = "Insufficient permissions."
