"""Tests for the custom exception hierarchy."""

import pytest

from app.core.exceptions import (
    ResearchOSError,
    NotFoundError,
    ValidationError,
    ExternalAPIError,
    RateLimitError,
    EmbeddingError,
    VectorStoreError,
    AgentError,
    WorkflowError,
)


class TestExceptionHierarchy:
    """Verify all exceptions inherit from ResearchOSError."""

    @pytest.mark.parametrize("exc_class", [
        NotFoundError,
        ValidationError,
        ExternalAPIError,
        RateLimitError,
        EmbeddingError,
        VectorStoreError,
        AgentError,
        WorkflowError,
    ])
    def test_inherits_from_base(self, exc_class):
        assert issubclass(exc_class, ResearchOSError)

    @pytest.mark.parametrize("exc_class", [
        NotFoundError,
        ValidationError,
        ExternalAPIError,
        RateLimitError,
        EmbeddingError,
        VectorStoreError,
        AgentError,
        WorkflowError,
    ])
    def test_inherits_from_exception(self, exc_class):
        assert issubclass(exc_class, Exception)


class TestExceptionStatusCodes:
    """Verify correct HTTP status codes."""

    def test_not_found_is_404(self):
        assert NotFoundError().status_code == 404

    def test_validation_is_422(self):
        assert ValidationError().status_code == 422

    def test_external_api_is_502(self):
        assert ExternalAPIError().status_code == 502

    def test_rate_limit_is_429(self):
        assert RateLimitError().status_code == 429

    def test_embedding_is_500(self):
        assert EmbeddingError().status_code == 500

    def test_vector_store_is_500(self):
        assert VectorStoreError().status_code == 500

    def test_agent_is_500(self):
        assert AgentError().status_code == 500

    def test_workflow_is_500(self):
        assert WorkflowError().status_code == 500


class TestExceptionCreation:
    """Test exception instantiation and serialization."""

    def test_default_detail(self):
        err = NotFoundError()
        assert err.detail == "The requested resource was not found."

    def test_custom_detail(self):
        err = NotFoundError("Project abc123 not found")
        assert err.detail == "Project abc123 not found"

    def test_custom_status_code(self):
        err = ResearchOSError("test", status_code=418)
        assert err.status_code == 418

    def test_context_dict(self):
        err = NotFoundError("Not found", context={"id": "abc123"})
        assert err.context == {"id": "abc123"}

    def test_empty_context_by_default(self):
        err = NotFoundError()
        assert err.context == {}

    def test_to_dict_basic(self):
        err = NotFoundError("Test error")
        d = err.to_dict()
        assert d["error"] == "NotFoundError"
        assert d["detail"] == "Test error"

    def test_to_dict_with_context(self):
        err = AgentError("Agent failed", context={"agent": "retrieval"})
        d = err.to_dict()
        assert "context" in d
        assert d["context"]["agent"] == "retrieval"

    def test_to_dict_without_context(self):
        err = NotFoundError()
        d = err.to_dict()
        assert "context" not in d

    def test_str_representation(self):
        err = NotFoundError("my error")
        assert str(err) == "my error"

    def test_raise_and_catch(self):
        with pytest.raises(ResearchOSError):
            raise NotFoundError("test")

    def test_catch_specific(self):
        with pytest.raises(NotFoundError):
            raise NotFoundError("test")
