"""Async arXiv API client for searching and retrieving academic papers.

Uses the public arXiv Atom XML feed at ``http://export.arxiv.org/api/query``
with strict adherence to the arXiv API rate-limit policy (≤1 request per
3 seconds).  Search results are optionally cached in Redis for 1 hour.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.core.exceptions import ExternalAPIError
from app.integrations.redis_client import RedisManager
from app.utils.logging import get_logger
from app.utils.retry import with_retry

logger = get_logger(__name__)

_ARXIV_BASE_URL = "http://export.arxiv.org/api/query"
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_OPENSEARCH_NS = "{http://a9.com/-/spec/opensearch/1.1/}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# Minimum interval between arXiv API requests (seconds).
_RATE_LIMIT_INTERVAL: float = 3.0

# Cache TTL for search results (seconds).
_CACHE_TTL: int = 3600  # 1 hour


@dataclass(frozen=True, slots=True)
class ArxivPaper:
    """Structured representation of an arXiv paper.

    Attributes:
        id: The arXiv identifier, e.g. ``2301.01234``.
        title: Paper title (whitespace-normalised).
        abstract: Full abstract text.
        authors: Ordered list of author names.
        published: Original publication timestamp.
        updated: Most recent update timestamp.
        categories: arXiv subject categories (primary first).
        doi: Digital Object Identifier, if available.
        pdf_url: Direct link to the PDF.
        comment: Author comment (e.g. page count, conference).
    """

    id: str
    title: str
    abstract: str
    authors: list[str]
    published: datetime
    updated: datetime
    categories: list[str]
    doi: str | None = None
    pdf_url: str = ""
    comment: str | None = None


class ArxivClient:
    """Async client for the arXiv search API.

    Instantiate once and reuse — the underlying ``httpx.AsyncClient``
    and rate-limiter are shared across calls.

    Args:
        use_cache: Whether to cache search results in Redis (default
            ``True``).  Caching is silently skipped when Redis is
            unavailable.
    """

    def __init__(self, *, use_cache: bool = True) -> None:
        self._use_cache = use_cache
        self._http: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def _get_http(self) -> httpx.AsyncClient:
        """Return a lazily-initialised ``httpx.AsyncClient``."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "ResearchOS/1.0 (async arXiv client)"},
            )
        return self._http

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def _wait_for_rate_limit(self) -> None:
        """Enforce ≤1 request per ``_RATE_LIMIT_INTERVAL`` seconds."""
        async with self._rate_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < _RATE_LIMIT_INTERVAL:
                wait = _RATE_LIMIT_INTERVAL - elapsed
                logger.debug("arxiv.rate_limit_wait", wait_seconds=round(wait, 2))
                await asyncio.sleep(wait)
            self._last_request_time = asyncio.get_event_loop().time()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(prefix: str, identifier: str) -> str:
        """Build a deterministic cache key."""
        digest = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"arxiv:{prefix}:{digest}"

    async def _cache_get(self, key: str) -> Any | None:
        if not self._use_cache:
            return None
        redis = RedisManager()
        return await redis.get(key)

    async def _cache_set(self, key: str, value: Any) -> None:
        if not self._use_cache:
            return
        redis = RedisManager()
        await redis.set(key, value, ttl=_CACHE_TTL)

    # ------------------------------------------------------------------
    # XML parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_entry(entry: ET.Element) -> ArxivPaper:
        """Parse a single ``<entry>`` element into an ``ArxivPaper``."""

        def _text(tag: str, ns: str = _ATOM_NS) -> str:
            el = entry.find(f"{ns}{tag}")
            return (el.text or "").strip() if el is not None else ""

        def _normalise(text: str) -> str:
            return re.sub(r"\s+", " ", text).strip()

        # ID — strip version suffix for canonical identifier.
        raw_id = _text("id")
        arxiv_id = raw_id.rsplit("/abs/", maxsplit=1)[-1]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

        # Authors
        authors = [
            (a.find(f"{_ATOM_NS}name").text or "").strip()
            for a in entry.findall(f"{_ATOM_NS}author")
            if a.find(f"{_ATOM_NS}name") is not None
        ]

        # Dates
        def _parse_dt(tag: str) -> datetime:
            raw = _text(tag)
            if not raw:
                return datetime.min
            # arXiv uses ISO 8601 with 'T' and 'Z'.
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))

        published = _parse_dt("published")
        updated = _parse_dt("updated")

        # Categories
        categories = [
            c.attrib.get("term", "")
            for c in entry.findall(f"{_ATOM_NS}category")
            if c.attrib.get("term")
        ]

        # PDF link
        pdf_url = ""
        for link in entry.findall(f"{_ATOM_NS}link"):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href", "")
                break

        # DOI (arXiv namespace)
        doi_el = entry.find(f"{_ARXIV_NS}doi")
        doi = (doi_el.text or "").strip() if doi_el is not None else None
        doi = doi or None

        # Comment
        comment_el = entry.find(f"{_ARXIV_NS}comment")
        comment = (comment_el.text or "").strip() if comment_el is not None else None
        comment = comment or None

        return ArxivPaper(
            id=arxiv_id,
            title=_normalise(_text("title")),
            abstract=_normalise(_text("summary")),
            authors=authors,
            published=published,
            updated=updated,
            categories=categories,
            doi=doi,
            pdf_url=pdf_url,
            comment=comment,
        )

    def _parse_feed(self, xml_bytes: bytes) -> list[ArxivPaper]:
        """Parse the full Atom feed and return a list of papers."""
        root = ET.fromstring(xml_bytes)
        entries = root.findall(f"{_ATOM_NS}entry")
        papers: list[ArxivPaper] = []
        for entry in entries:
            try:
                papers.append(self._parse_entry(entry))
            except Exception as exc:  # noqa: BLE001 — never crash on one bad entry
                logger.warning("arxiv.parse_entry_failed", error=str(exc))
        return papers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @with_retry(max_retries=3, retryable_exceptions=(httpx.HTTPStatusError, httpx.RequestError))
    async def search(
        self,
        query: str,
        max_results: int = 20,
        *,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        start: int = 0,
    ) -> list[ArxivPaper]:
        """Search arXiv for papers matching *query*.

        Args:
            query: arXiv search query (supports field prefixes like
                ``au:``, ``ti:``, ``cat:``).
            max_results: Maximum number of results (capped at 100 by
                arXiv API).
            sort_by: ``"relevance"`` or ``"lastUpdatedDate"`` or
                ``"submittedDate"``.
            sort_order: ``"ascending"`` or ``"descending"``.
            start: Offset for pagination.

        Returns:
            List of :class:`ArxivPaper` objects.

        Raises:
            ExternalAPIError: On HTTP or parsing failures.
        """
        max_results = min(max_results, 100)

        # Check cache first
        cache_id = f"{query}:{max_results}:{sort_by}:{sort_order}:{start}"
        cache_key = self._cache_key("search", cache_id)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("arxiv.cache_hit", query=query)
            return [ArxivPaper(**p) for p in cached]

        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        await self._wait_for_rate_limit()
        client = await self._get_http()

        try:
            response = await client.get(_ARXIV_BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "arxiv.search_http_error",
                status=exc.response.status_code,
                query=query,
            )
            raise ExternalAPIError(
                f"arXiv API returned HTTP {exc.response.status_code}",
                service="arxiv",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("arxiv.search_request_error", query=query, error=str(exc))
            raise ExternalAPIError(
                f"arXiv API request failed: {exc}",
                service="arxiv",
            ) from exc

        try:
            papers = self._parse_feed(response.content)
        except ET.ParseError as exc:
            logger.error("arxiv.xml_parse_error", query=query, error=str(exc))
            raise ExternalAPIError(
                "Failed to parse arXiv API response XML",
                service="arxiv",
            ) from exc

        logger.info("arxiv.search_complete", query=query, results=len(papers))

        # Populate cache
        await self._cache_set(cache_key, [asdict(p) for p in papers])

        return papers

    async def get_paper(self, arxiv_id: str) -> ArxivPaper:
        """Retrieve metadata for a single paper by its arXiv ID.

        Args:
            arxiv_id: Bare arXiv identifier, e.g. ``"2301.01234"``.

        Returns:
            An :class:`ArxivPaper` instance.

        Raises:
            ExternalAPIError: If the paper is not found or the API
                returns an error.
        """
        cache_key = self._cache_key("paper", arxiv_id)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("arxiv.paper_cache_hit", arxiv_id=arxiv_id)
            return ArxivPaper(**cached)

        await self._wait_for_rate_limit()
        client = await self._get_http()

        params = {"id_list": arxiv_id, "max_results": 1}
        try:
            response = await client.get(_ARXIV_BASE_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "arxiv.get_paper_http_error",
                status=exc.response.status_code,
                arxiv_id=arxiv_id,
            )
            raise ExternalAPIError(
                f"arXiv API returned HTTP {exc.response.status_code}",
                service="arxiv",
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "arxiv.get_paper_request_error",
                arxiv_id=arxiv_id,
                error=str(exc),
            )
            raise ExternalAPIError(
                f"arXiv API request failed: {exc}",
                service="arxiv",
            ) from exc

        papers = self._parse_feed(response.content)
        if not papers:
            raise ExternalAPIError(
                f"Paper {arxiv_id} not found on arXiv",
                service="arxiv",
            )

        paper = papers[0]
        await self._cache_set(cache_key, asdict(paper))
        logger.info("arxiv.get_paper_complete", arxiv_id=arxiv_id, title=paper.title)
        return paper

    async def download_pdf(self, arxiv_id: str, save_path: str | Path) -> Path:
        """Download the PDF for *arxiv_id* to *save_path*.

        Args:
            arxiv_id: Bare arXiv identifier, e.g. ``"2301.01234"``.
            save_path: Directory or full file path where the PDF should
                be saved.  If a directory, the file is named
                ``<arxiv_id>.pdf``.

        Returns:
            Resolved :class:`Path` to the downloaded file.

        Raises:
            ExternalAPIError: On download failure.
        """
        save_path = Path(save_path)
        if save_path.is_dir():
            safe_name = arxiv_id.replace("/", "_")
            save_path = save_path / f"{safe_name}.pdf"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        await self._wait_for_rate_limit()
        client = await self._get_http()

        try:
            response = await client.get(pdf_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "arxiv.download_http_error",
                status=exc.response.status_code,
                arxiv_id=arxiv_id,
            )
            raise ExternalAPIError(
                f"Failed to download PDF for {arxiv_id}: HTTP {exc.response.status_code}",
                service="arxiv",
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "arxiv.download_request_error",
                arxiv_id=arxiv_id,
                error=str(exc),
            )
            raise ExternalAPIError(
                f"PDF download request failed: {exc}",
                service="arxiv",
            ) from exc

        save_path.write_bytes(response.content)
        logger.info(
            "arxiv.pdf_downloaded",
            arxiv_id=arxiv_id,
            path=str(save_path),
            size_bytes=len(response.content),
        )
        return save_path.resolve()
