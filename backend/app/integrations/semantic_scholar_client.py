"""Async Semantic Scholar API client.

Provides access to the Semantic Scholar Academic Graph v1 endpoints for
paper search, metadata retrieval, citations, and references.

Rate limits:
- **Without** API key: 100 requests per 5 minutes (~0.33 req/s).
- **With** API key: 1 request per second.

The client automatically detects whether an API key is configured and
adapts its rate limiting accordingly.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from app.config import get_settings
from app.core.exceptions import ExternalAPIError
from app.integrations.redis_client import RedisManager
from app.utils.logging import get_logger
from app.utils.retry import with_retry

logger = get_logger(__name__)

_S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"
_CACHE_TTL = 3600  # 1 hour

# Default fields requested if the caller does not specify any.
_DEFAULT_PAPER_FIELDS = (
    "paperId,title,abstract,authors,year,venue,citationCount,"
    "referenceCount,doi,url,fieldsOfStudy,tldr,externalIds"
)


@dataclass(slots=True)
class S2Paper:
    """Structured representation of a Semantic Scholar paper.

    Attributes:
        paperId: Unique Semantic Scholar paper identifier.
        title: Paper title.
        abstract: Abstract text (may be ``None`` for some papers).
        authors: List of author dicts with ``authorId`` and ``name``.
        year: Publication year.
        venue: Publication venue.
        citationCount: Number of citations.
        referenceCount: Number of references.
        doi: Digital Object Identifier.
        url: Semantic Scholar URL.
        fieldsOfStudy: List of field-of-study strings.
        tldr: Auto-generated TL;DR dict (``model``, ``text``).
        externalIds: Mapping of external IDs (e.g. DOI, ArXiv).
    """

    paperId: str = ""
    title: str = ""
    abstract: str | None = None
    authors: list[dict[str, Any]] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    citationCount: int = 0
    referenceCount: int = 0
    doi: str | None = None
    url: str = ""
    fieldsOfStudy: list[str] = field(default_factory=list)
    tldr: dict[str, Any] | None = None
    externalIds: dict[str, str] = field(default_factory=dict)


class SemanticScholarClient:
    """Async client for the Semantic Scholar Academic Graph API.

    Usage::

        async with SemanticScholarClient() as s2:
            papers = await s2.search("transformer attention")
            paper = await s2.get_paper("649def34f8be52c8b66281af98ae884c09aef38b")
    """

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._api_key: str | None = None
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()
        self._rate_interval: float = 1.0  # default (with key)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            settings = get_settings()
            self._api_key = getattr(settings, "SEMANTIC_SCHOLAR_API_KEY", None)
            if self._api_key in (None, "", "your-semantic-scholar-api-key"):
                self._api_key = None

            headers: dict[str, str] = {
                "User-Agent": "ResearchOS/1.0 (Semantic Scholar client)",
            }
            if self._api_key:
                headers["x-api-key"] = self._api_key
                self._rate_interval = 1.0
            else:
                # 100 requests per 5 min = 3 seconds between requests
                self._rate_interval = 3.0

            self._http = httpx.AsyncClient(
                base_url=_S2_BASE_URL,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers=headers,
            )
        return self._http

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> SemanticScholarClient:
        await self._get_http()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Rate limiter
    # ------------------------------------------------------------------

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_interval:
                wait = self._rate_interval - elapsed
                logger.debug("s2.rate_limit_wait", wait_seconds=round(wait, 2))
                await asyncio.sleep(wait)
            self._last_request_time = asyncio.get_event_loop().time()

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Issue a rate-limited HTTP request with retry on 429."""
        client = await self._get_http()

        for attempt in range(1, max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                response = await client.request(method, path, params=params)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(
                        "s2.rate_limited",
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise ExternalAPIError(
                        f"Resource not found at {path}",
                        service="semantic_scholar",
                    ) from exc
                if attempt == max_retries:
                    raise ExternalAPIError(
                        f"S2 API error HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                        service="semantic_scholar",
                    ) from exc
                await asyncio.sleep(2**attempt)
            except httpx.RequestError as exc:
                if attempt == max_retries:
                    raise ExternalAPIError(
                        f"S2 API request failed: {exc}",
                        service="semantic_scholar",
                    ) from exc
                await asyncio.sleep(2**attempt)

        raise ExternalAPIError(
            "S2 API max retries exhausted",
            service="semantic_scholar",
        )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _cache_get(key: str) -> Any | None:
        redis = RedisManager()
        return await redis.get(key)

    @staticmethod
    async def _cache_set(key: str, value: Any) -> None:
        redis = RedisManager()
        await redis.set(key, value, ttl=_CACHE_TTL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @with_retry(max_retries=3, retryable_exceptions=(httpx.HTTPStatusError, httpx.RequestError))
    async def search(
        self,
        query: str,
        limit: int = 20,
        fields: str | None = None,
    ) -> list[S2Paper]:
        """Search for papers matching *query*.

        Args:
            query: Free-text search query.
            limit: Maximum number of results (1–100).
            fields: Comma-separated field names.  Uses
                ``_DEFAULT_PAPER_FIELDS`` when ``None``.

        Returns:
            List of :class:`S2Paper` instances.

        Raises:
            ExternalAPIError: On API failure.
        """
        limit = max(1, min(limit, 100))
        fields = fields or _DEFAULT_PAPER_FIELDS

        cache_key = f"s2:search:{query}:{limit}:{fields}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("s2.cache_hit", query=query)
            return [S2Paper(**p) for p in cached]

        data = await self._request(
            "GET",
            "/paper/search",
            params={"query": query, "limit": limit, "fields": fields},
        )

        papers = [
            self._dict_to_paper(item) for item in data.get("data", [])
        ]
        logger.info("s2.search_complete", query=query, results=len(papers))
        await self._cache_set(cache_key, [asdict(p) for p in papers])
        return papers

    async def get_paper(
        self,
        paper_id: str,
        fields: str | None = None,
    ) -> S2Paper:
        """Retrieve metadata for a single paper.

        Args:
            paper_id: Semantic Scholar paper ID, DOI, arXiv ID
                (prefixed ``ARXIV:``), or other supported identifier.
            fields: Comma-separated field names.

        Returns:
            A populated :class:`S2Paper`.

        Raises:
            ExternalAPIError: If the paper is not found or the API
                returns an error.
        """
        fields = fields or _DEFAULT_PAPER_FIELDS

        cache_key = f"s2:paper:{paper_id}:{fields}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return S2Paper(**cached)

        data = await self._request(
            "GET",
            f"/paper/{paper_id}",
            params={"fields": fields},
        )

        paper = self._dict_to_paper(data)
        logger.info("s2.get_paper_complete", paper_id=paper_id, title=paper.title)
        await self._cache_set(cache_key, asdict(paper))
        return paper

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
        fields: str | None = None,
    ) -> list[S2Paper]:
        """Return papers that cite the given paper.

        Args:
            paper_id: Semantic Scholar paper identifier.
            limit: Maximum number of citing papers.
            fields: Comma-separated field names for the citing papers.

        Returns:
            List of citing :class:`S2Paper` objects.
        """
        limit = max(1, min(limit, 1000))
        citing_fields = fields or "paperId,title,abstract,authors,year,venue,citationCount,doi,url"

        data = await self._request(
            "GET",
            f"/paper/{paper_id}/citations",
            params={"limit": limit, "fields": citing_fields},
        )

        papers: list[S2Paper] = []
        for item in data.get("data", []):
            citing = item.get("citingPaper")
            if citing:
                papers.append(self._dict_to_paper(citing))

        logger.info(
            "s2.citations_complete",
            paper_id=paper_id,
            results=len(papers),
        )
        return papers

    async def get_references(
        self,
        paper_id: str,
        limit: int = 100,
        fields: str | None = None,
    ) -> list[S2Paper]:
        """Return papers referenced by the given paper.

        Args:
            paper_id: Semantic Scholar paper identifier.
            limit: Maximum number of referenced papers.
            fields: Comma-separated field names.

        Returns:
            List of referenced :class:`S2Paper` objects.
        """
        limit = max(1, min(limit, 1000))
        ref_fields = fields or "paperId,title,abstract,authors,year,venue,citationCount,doi,url"

        data = await self._request(
            "GET",
            f"/paper/{paper_id}/references",
            params={"limit": limit, "fields": ref_fields},
        )

        papers: list[S2Paper] = []
        for item in data.get("data", []):
            cited = item.get("citedPaper")
            if cited:
                papers.append(self._dict_to_paper(cited))

        logger.info(
            "s2.references_complete",
            paper_id=paper_id,
            results=len(papers),
        )
        return papers

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dict_to_paper(raw: dict[str, Any]) -> S2Paper:
        """Safely convert a raw API dict to an ``S2Paper``."""
        return S2Paper(
            paperId=raw.get("paperId", ""),
            title=raw.get("title", ""),
            abstract=raw.get("abstract"),
            authors=raw.get("authors") or [],
            year=raw.get("year"),
            venue=raw.get("venue", ""),
            citationCount=raw.get("citationCount") or 0,
            referenceCount=raw.get("referenceCount") or 0,
            doi=raw.get("doi") or raw.get("externalIds", {}).get("DOI"),
            url=raw.get("url", ""),
            fieldsOfStudy=raw.get("fieldsOfStudy") or [],
            tldr=raw.get("tldr"),
            externalIds=raw.get("externalIds") or {},
        )
