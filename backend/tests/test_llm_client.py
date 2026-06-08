"""Tests for the LLM client.

Uses mocked HTTP responses — no real API calls.
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from app.integrations.llm_client import LLMClient


@pytest.fixture
def llm_client():
    """Create an LLMClient with test settings."""
    with patch("app.integrations.llm_client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.mistral_api_key = "test-mistral-key"
        settings.mistral_model = "mistral-test"
        settings.kimi_api_key = "test-kimi-key"
        settings.kimi_model = "kimi-test"
        settings.kimi_base_url = "https://api.test.com/v1"
        mock_settings.return_value = settings
        yield LLMClient()


class TestLLMClientGenerate:
    """Test the generate() method."""

    @pytest.mark.asyncio
    async def test_invalid_provider_raises(self, llm_client):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            await llm_client.generate(
                provider="invalid",
                system_prompt="test",
                user_prompt="test",
            )


class TestLLMClientMissingKeys:
    """Test graceful handling when API keys are missing."""

    @pytest.mark.asyncio
    async def test_mistral_no_key(self):
        with patch("app.integrations.llm_client.get_settings") as mock:
            settings = MagicMock()
            settings.mistral_api_key = ""
            settings.mistral_model = "test"
            mock.return_value = settings
            client = LLMClient()

            result = await client.generate("mistral", "sys", "user")
            assert "not configured" in result.lower() or "placeholder" in result.lower()

    @pytest.mark.asyncio
    async def test_kimi_no_key(self):
        with patch("app.integrations.llm_client.get_settings") as mock:
            settings = MagicMock()
            settings.kimi_api_key = ""
            settings.kimi_model = "test"
            settings.kimi_base_url = "https://test.com"
            mock.return_value = settings
            client = LLMClient()

            result = await client.generate("kimi", "sys", "user")
            assert "not configured" in result.lower() or "placeholder" in result.lower()


class TestLLMClientGenerateJSON:
    """Test JSON parsing logic."""

    @pytest.mark.asyncio
    async def test_strips_code_fences(self):
        with patch("app.integrations.llm_client.get_settings") as mock:
            settings = MagicMock()
            settings.mistral_api_key = ""
            mock.return_value = settings
            client = LLMClient()

        # Test the fence stripping indirectly through generate_json
        # by mocking the generate method
        with patch.object(client, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = '```json\n{"key": "value"}\n```'
            result = await client.generate_json("mistral", "sys", "user")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_handles_plain_json(self):
        with patch("app.integrations.llm_client.get_settings") as mock:
            settings = MagicMock()
            settings.mistral_api_key = ""
            mock.return_value = settings
            client = LLMClient()

        with patch.object(client, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = '{"result": 42}'
            result = await client.generate_json("mistral", "sys", "user")
            assert result == {"result": 42}

    @pytest.mark.asyncio
    async def test_handles_parse_error(self):
        with patch("app.integrations.llm_client.get_settings") as mock:
            settings = MagicMock()
            settings.mistral_api_key = ""
            mock.return_value = settings
            client = LLMClient()

        with patch.object(client, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "This is not JSON at all"
            result = await client.generate_json("mistral", "sys", "user")
            assert result.get("parse_error") is True
            assert "raw_response" in result
