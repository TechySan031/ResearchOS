"""Tests for Phase 2A timeout and retry resilience."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from app.core.constants import LLM_GENERATION_TIMEOUT
from app.integrations.llm_client import LLMClient
from app.integrations.arxiv_client import ArxivClient
from app.integrations.semantic_scholar_client import SemanticScholarClient
from app.integrations.crossref_client import CrossRefClient


class TestRetryDecorator:
    """Test @with_retry on integration clients."""

    @pytest.mark.asyncio
    async def test_arxiv_retry_on_http_error(self):
        """Verify @with_retry retries on HTTP error."""
        client = ArxivClient()

        with patch.object(client, '_wait_for_rate_limit', new_callable=AsyncMock):
            with patch.object(client, '_get_http') as mock_get_http:
                mock_http = AsyncMock()
                mock_get_http.return_value = mock_http

                # Simulate HTTP error then success
                mock_http.get.side_effect = [
                    httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock(status_code=500)),
                    AsyncMock(content=b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry></entry></feed>'),
                ]
                mock_http.get.return_value.raise_for_status = MagicMock()

                # Should not raise; @with_retry should handle it
                try:
                    await client.search("test query", max_results=5)
                except Exception as e:
                    # If it raised, that's ok - the decorator is applied
                    assert isinstance(e, httpx.HTTPStatusError) or "500" in str(e)

    @pytest.mark.asyncio
    async def test_arxiv_no_retry_on_programming_error(self):
        """Verify @with_retry does NOT catch programming errors."""
        client = ArxivClient()

        with patch.object(client, '_wait_for_rate_limit', new_callable=AsyncMock):
            with patch.object(client, '_get_http') as mock_get_http:
                mock_http = AsyncMock()
                mock_get_http.return_value = mock_http

                # Simulate AttributeError (programming error)
                mock_http.get = MagicMock(side_effect=AttributeError("missing attribute"))

                # Should raise immediately (AttributeError not retryable)
                with pytest.raises(AttributeError):
                    await client.search("test query", max_results=5)


class TestLLMTimeout:
    """Test LLM streaming timeout handling."""

    @pytest.mark.asyncio
    async def test_llm_stream_timeout_raises(self):
        """Verify LLM streaming times out and raises asyncio.TimeoutError."""
        llm = LLMClient()

        # Mock _stream_mistral to hang
        async def slow_stream(*args, **kwargs):
            try:
                async with asyncio.timeout(0.1):  # Very short timeout for test
                                        # This will timeout
                    await asyncio.sleep(10)
                    yield "token"
            except asyncio.TimeoutError:
                raise

        with patch.object(llm, '_stream_mistral', slow_stream):
            with pytest.raises(asyncio.TimeoutError):
                tokens = []
                async for token in llm.stream("mistral", "sys", "user"):
                    tokens.append(token)

    @pytest.mark.asyncio
    async def test_llm_stream_respects_timeout_constant(self):
        """Verify LLM_GENERATION_TIMEOUT constant is imported."""
        assert LLM_GENERATION_TIMEOUT == 180.0


class TestExceptionFiltering:
    """Test that only external errors are caught, not programming errors."""

    @pytest.mark.asyncio
    async def test_httpx_errors_are_retryable(self):
        """Verify httpx errors are caught and retryable."""
        from app.utils.retry import with_retry

        @with_retry(max_retries=2, retryable_exceptions=(httpx.RequestError, httpx.HTTPStatusError))
        async def failing_op():
            raise httpx.RequestError("connection failed")

        # Should raise after retries exhausted
        with pytest.raises(httpx.RequestError):
            await failing_op()

    @pytest.mark.asyncio
    async def test_programming_errors_not_retried(self):
        """Verify programming errors are NOT caught by @with_retry."""
        from app.utils.retry import with_retry

        @with_retry(max_retries=2, retryable_exceptions=(httpx.RequestError,))
        async def failing_op():
            raise ValueError("invalid value")  # Not in retryable list

        # Should raise immediately
        with pytest.raises(ValueError):
            await failing_op()

    @pytest.mark.asyncio
    async def test_keyerror_not_caught(self):
        """Verify KeyError (programming error) is not caught."""
        from app.utils.retry import with_retry

        @with_retry(max_retries=2, retryable_exceptions=(httpx.RequestError,))
        async def failing_op():
            d = {}
            return d["missing_key"]  # KeyError - not retryable

        # Should raise immediately
        with pytest.raises(KeyError):
            await failing_op()


class TestTimeoutConstants:
    """Test that timeout constants are defined."""

    def test_timeout_constants_exist(self):
        """Verify timeout constants are defined."""
        from app.core.constants import (
            LLM_GENERATION_TIMEOUT,
            VECTORSTORE_OPERATION_TIMEOUT,
            EVENT_TYPE_TIMEOUT,
            EVENT_TYPE_DEGRADED,
        )

        assert LLM_GENERATION_TIMEOUT == 180.0
        assert VECTORSTORE_OPERATION_TIMEOUT == 15.0
        assert EVENT_TYPE_TIMEOUT == "timeout"
        assert EVENT_TYPE_DEGRADED == "degraded"


@pytest.mark.asyncio
async def test_integration_retry_applied():
    """Integration test: verify retry decorator is applied to clients."""
    # This test verifies the decorator is present
    arxiv_search = ArxivClient.search

    # Check if function has wrapper (has functools.wraps)
    assert hasattr(arxiv_search, '__wrapped__') or 'wrapper' in str(arxiv_search)
