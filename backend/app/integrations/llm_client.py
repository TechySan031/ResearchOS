"""
ResearchOS — Unified LLM Client

Provides async interfaces to Mistral and Kimi (OpenAI-compatible)
models with structured output support, streaming, and retry logic.

Usage::

    llm = LLMClient()
    response = await llm.generate(
        provider="mistral",
        system_prompt="You are a research assistant.",
        user_prompt="Summarize this paper.",
    )
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Optional

import httpx

from app.config import get_settings
from app.core.constants import LLM_GENERATION_TIMEOUT
from app.utils.logging import get_logger
from app.utils.retry import with_retry

logger = get_logger(__name__)


class LLMClient:
    """Unified async LLM client for Mistral and Kimi APIs."""

    def __init__(self):
        self._settings = get_settings()

    # ── Core generation ─────────────────────────────────────────────

    @with_retry(max_retries=3)
    async def generate(
        self,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> str:
        """
        Generate a completion from the specified LLM provider.

        Args:
            provider: "mistral" or "kimi".
            system_prompt: System-level instructions.
            user_prompt: User message / context.
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens in response.
            response_format: Optional "json_object" for structured output.

        Returns:
            The generated text string.
        """
        if provider == "mistral":
            return await self._call_mistral(
                system_prompt, user_prompt, temperature, max_tokens, response_format
            )
        elif provider == "kimi":
            return await self._call_kimi(
                system_prompt, user_prompt, temperature, max_tokens, response_format
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def generate_json(
        self,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict:
        """Generate and parse a JSON response from the LLM."""
        raw = await self.generate(
            provider=provider,
            system_prompt=system_prompt + "\n\nRespond ONLY with valid JSON.",
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("llm_json_parse_failed", raw_preview=raw[:200])
            return {"raw_response": raw, "parse_error": True}

    async def stream(
        self,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM provider."""
        if provider == "kimi":
            async for token in self._stream_kimi(
                system_prompt, user_prompt, temperature, max_tokens
            ):
                yield token
        elif provider == "mistral":
            async for token in self._stream_mistral(
                system_prompt, user_prompt, temperature, max_tokens
            ):
                yield token
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ── Mistral ─────────────────────────────────────────────────────

    async def _call_mistral(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        api_key = self._settings.mistral_api_key
        model = self._settings.mistral_model

        if not api_key:
            logger.warning("mistral_api_key_not_set")
            return "[Mistral API key not configured — using placeholder response]"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json_object":
            body["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        logger.info(
            "llm.mistral.complete",
            model=model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
        return content

    async def _stream_mistral(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        api_key = self._settings.mistral_api_key
        if not api_key:
            yield "[Mistral API key not configured]"
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._settings.mistral_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with asyncio.timeout(LLM_GENERATION_TIMEOUT):
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        "https://api.mistral.ai/v1/chat/completions",
                        headers=headers,
                        json=body,
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                payload = line[6:]
                                if payload.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(payload)
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                                except (json.JSONDecodeError, KeyError, IndexError):
                                    continue
        except asyncio.TimeoutError:
            logger.warning("llm.mistral_stream_timeout")
            raise

    # ── Kimi (OpenAI-compatible) ────────────────────────────────────

    async def _call_kimi(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        api_key = self._settings.kimi_api_key
        model = self._settings.kimi_model
        base_url = self._settings.kimi_base_url

        if not api_key:
            logger.warning("kimi_api_key_not_set")
            return "[Kimi API key not configured — using placeholder response]"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json_object":
            body["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        logger.info(
            "llm.kimi.complete",
            model=model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
        return content

    async def _stream_kimi(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        api_key = self._settings.kimi_api_key
        if not api_key:
            yield "[Kimi API key not configured]"
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._settings.kimi_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with asyncio.timeout(LLM_GENERATION_TIMEOUT):
                async with httpx.AsyncClient(timeout=180.0) as client:
                    async with client.stream(
                        "POST",
                        f"{self._settings.kimi_base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                payload = line[6:]
                                if payload.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(payload)
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                                except (json.JSONDecodeError, KeyError, IndexError):
                                    continue
        except asyncio.TimeoutError:
            logger.warning("llm.kimi_stream_timeout")
            raise
