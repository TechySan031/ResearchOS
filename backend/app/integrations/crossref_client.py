"""Async CrossRef API client for DOI metadata and verification.

Uses the public CrossRef REST API at ``https://api.crossref.org/works``
with "polite pool" headers (``mailto``) for improved rate-limit
allowances.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.core.exceptions import ExternalAPIError
from app.integrations.redis_client import RedisManager
from app.utils.logging import get_logger
from app.utils.retry import with_retry

logger = get_logger(__name__)

_CROSSREF_BASE_URL = "https://api.crossref.org/works"
_CACHE_TTL = 3600  # 1 hour

# CrossRef polite pool – set a contact email so requests are routed to
# the higher-priority queue.
_MAILTO = "researchos@example.com"


@dataclass(slots=True)
class CrossRefWork:
    """Structured representation of a CrossRef work (publication).

    Attributes:
        doi: Digital Object Identifier.
        title: Work title.
        authors: List of author dicts with ``given`` and ``family`` keys.
        published_date: Earliest available publication date.
        venue: Container title (journal / conference name).
        type: Work type (``journal-article``, ``proceedings-article``, etc.).
        url: DOI URL.
        references_count: Number of references made by this work.
        is_referenced_by_count: Number of times this work is cited.
        abstract: Abstract text (may be ``None`` — CrossRef coverage is
            partial).
    """

    doi: str = ""
    title: str = ""
    authors: list[dict[str, str]] = field(default_factory=list)
    published_date: str | None = None
    venue: str = ""
    type: str = ""
    url: str = ""
    references_count: int = 0
    is_referenced_by_count: int = 0
    abstract: str | None = None


class CrossRefClient:
    """Async client for the CrossRef REST API.

    Usage::

        async with CrossRefClient() as cr:
            works = await cr.search("deep learning")
            work = await cr.get_by_doi("10.1038/s41586-021-03819-2")
            ok = await cr.verify_doi("10.1038/s41586-021-03819-2")
    """

    def __init__(self, *, mailto: str = _MAILTO) -> None:
        self._mailto = mailto
        self._http: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()
        # CrossRef polite pool: ~50 req/s — we stay conservative at 10 req/s.
        self._rate_interval: float = 0.1

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": f"ResearchOS/1.0 (mailto:{self._mailto})",
                },
            )
        return self._http

    async def close(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> CrossRefClient:
        await self._get_http()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_interval:
                await asyncio.sleep(self._rate_interval - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    async def _request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        client = await self._get_http()

        for attempt in range(1, max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                response = await client.get(url, params=params)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(
                        "crossref.rate_limited",
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
                        f"CrossRef resource not found: {url}",
                        service="crossref",
                    ) from exc
                if attempt == max_retries:
                    raise ExternalAPIError(
                        f"CrossRef API error HTTP {exc.response.status_code}",
                        service="crossref",
                    ) from exc
                await asyncio.sleep(2**attempt)
            except httpx.RequestError as exc:
                if attempt == max_retries:
                    raise ExternalAPIError(
                        f"CrossRef API request failed: {exc}",
                        service="crossref",
                    ) from exc
                await asyncio.sleep(2**attempt)

        raise ExternalAPIError(
            "CrossRef API max retries exhausted",
            service="crossref",
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
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_work(raw: dict[str, Any]) -> CrossRefWork:
        """Convert a raw CrossRef API work item to ``CrossRefWork``."""
        # Title — CrossRef stores titles as a list.
        titles = raw.get("title") or []
        title = titles[0] if titles else ""

        # Authors
        authors_raw = raw.get("author") or []
        authors = [
            {"given": a.get("given", ""), "family": a.get("family", "")}
            for a in authors_raw
        ]

        # Published date — prefer 'published-print', fall back to
        # 'published-online', then 'created'.
        pub_date: str | None = None
        for key in ("published-print", "published-online", "created"):
            date_obj = raw.get(key)
            if date_obj and "date-parts" in date_obj:
                parts = date_obj["date-parts"][0]
                if parts:
                    try:
                        year = int(parts[0])
                        month = int(parts[1]) if len(parts) > 1 else 1
                        day = int(parts[2]) if len(parts) > 2 else 1
                        pub_date = date(year, month, day).isoformat()
                        break
                    except (ValueError, TypeError, IndexError):
                        continue

        # Container title (venue / journal)
        container = raw.get("container-title") or []
        venue = container[0] if container else ""

        # Abstract — CrossRef sometimes includes JATS XML; strip tags.
        abstract = raw.get("abstract")
        if abstract:
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()

        return CrossRefWork(
            doi=raw.get("DOI", ""),
            title=title,
            authors=authors,
            published_date=pub_date,
            venue=venue,
            type=raw.get("type", ""),
            url=raw.get("URL", ""),
            references_count=raw.get("references-count", 0),
            is_referenced_by_count=raw.get("is-referenced-by-count", 0),
            abstract=abstract,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @with_retry(max_retries=3, retryable_exceptions=(httpx.HTTPStatusError, httpx.RequestError))
    async def search(
        self,
        query: str,
        rows: int = 20,
        *,
        sort: str = "relevance",
        order: str = "desc",
    ) -> list[CrossRefWork]:
        """Search CrossRef for works matching *query*.

        Args:
            query: Free-text search query.
            rows: Number of results (max 1000).
            sort: Sort field (``relevance``, ``published``, etc.).
            order: ``asc`` or ``desc``.

        Returns:
            List of :class:`CrossRefWork` instances.

        Raises:
            ExternalAPIError: On API failure.
        """
        rows = max(1, min(rows, 1000))

        cache_key = f"crossref:search:{query}:{rows}:{sort}:{order}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.debug("crossref.cache_hit", query=query)
            return [CrossRefWork(**w) for w in cached]

        params: dict[str, Any] = {
            "query": query,
            "rows": rows,
            "sort": sort,
            "order": order,
            "mailto": self._mailto,
        }

        data = await self._request(_CROSSREF_BASE_URL, params=params)

        items = data.get("message", {}).get("items", [])
        works = [self._parse_work(item) for item in items]

        logger.info("crossref.search_complete", query=query, results=len(works))
        await self._cache_set(cache_key, [asdict(w) for w in works])
        return works

    async def get_by_doi(self, doi: str) -> CrossRefWork:
        """Retrieve metadata for a single work by DOI.

        Args:
            doi: A valid Digital Object Identifier, e.g.
                ``"10.1038/s41586-021-03819-2"``.

        Returns:
            A populated :class:`CrossRefWork`.

        Raises:
            ExternalAPIError: If the DOI is not found.
        """
        doi = doi.strip().strip("/")

        cache_key = f"crossref:doi:{doi}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return CrossRefWork(**cached)

        url = f"{_CROSSREF_BASE_URL}/{doi}"
        params = {"mailto": self._mailto}

        data = await self._request(url, params=params)
        work = self._parse_work(data.get("message", {}))
        logger.info("crossref.get_by_doi_complete", doi=doi, title=work.title)
        await self._cache_set(cache_key, asdict(work))
        return work

    async def verify_doi(self, doi: str) -> bool:
        """Check whether a DOI exists in CrossRef.

        Args:
            doi: The DOI to verify.

        Returns:
            ``True`` if the DOI resolves to a valid work, ``False``
            otherwise.
        """
        doi = doi.strip().strip("/")
        url = f"{_CROSSREF_BASE_URL}/{doi}"
        client = await self._get_http()

        await self._wait_for_rate_limit()
        try:
            response = await client.head(
                url, params={"mailto": self._mailto}
            )
            exists = response.status_code == 200
            logger.info("crossref.verify_doi", doi=doi, exists=exists)
            return exists
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("crossref.verify_doi_failed", doi=doi, error=str(exc))
            return False
