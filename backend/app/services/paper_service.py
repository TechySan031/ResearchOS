"""Paper management service.

Coordinates with external API clients (arXiv, Semantic Scholar, CrossRef),
handles deduplication, and persists paper metadata to the database.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
import datetime as _dt
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.integrations.arxiv_client import ArxivClient
from app.integrations.semantic_scholar_client import SemanticScholarClient
from app.integrations.crossref_client import CrossRefClient
from app.models.database import Paper, get_async_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Internal helpers ────────────────────────────────────────────────────

_STOP_WORDS = frozenset(
    {"a", "an", "the", "of", "and", "in", "to", "for", "on", "with", "is", "at", "by"}
)


def _normalise_title(title: str) -> str:
    """Lower-case, strip punctuation and stop-words."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    tokens = [t for t in title.split() if t not in _STOP_WORDS]
    return " ".join(tokens)


def _title_hash(title: str) -> str:
    return hashlib.md5(_normalise_title(title).encode()).hexdigest()


def _deduplicate(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by DOI then normalised title hash."""
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict[str, Any]] = []
    for p in papers:
        doi = (p.get("doi") or "").strip().lower()
        t_hash = _title_hash(p.get("title", ""))
        if doi and doi in seen_dois:
            continue
        if t_hash in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        seen_titles.add(t_hash)
        unique.append(p)
    return unique


# ── Service ─────────────────────────────────────────────────────────────


class PaperService:
    """Service for searching, retrieving, and persisting paper metadata."""

    # ── SEARCH ──────────────────────────────────────────────────────

    @staticmethod
    async def search_papers(
        project_id: str,
        query: str,
        sources: list[str] | None = None,
        *,
        max_results_per_source: int = 15,
    ) -> list[dict[str, Any]]:
        """Search external databases for papers and return unified results.

        Papers are **not** persisted automatically — call ``save_papers``
        to persist selected results.

        Args:
            project_id: The owning project (used for provenance tagging).
            query: Natural-language search query.
            sources: Which sources to search.  Defaults to all three:
                ``["arxiv", "semantic_scholar", "crossref"]``.
            max_results_per_source: Max results to fetch per source.

        Returns:
            Deduplicated list of paper metadata dicts.
        """
        if sources is None:
            sources = ["arxiv", "semantic_scholar", "crossref"]

        logger.info(
            "paper_service.search",
            project_id=project_id,
            query=query,
            sources=sources,
        )

        coros: list[Any] = []
        source_order: list[str] = []

        if "arxiv" in sources:
            coros.append(_search_arxiv(query, max_results_per_source))
            source_order.append("arxiv")
        if "semantic_scholar" in sources:
            coros.append(_search_semantic_scholar(query, max_results_per_source))
            source_order.append("semantic_scholar")
        if "crossref" in sources:
            coros.append(_search_crossref(query, max_results_per_source))
            source_order.append("crossref")

        results = await asyncio.gather(*coros, return_exceptions=True)

        all_papers: list[dict[str, Any]] = []
        for idx, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(
                    "paper_service.search_source_error",
                    source=source_order[idx],
                    error=str(result),
                )
                continue
            all_papers.extend(result)

        deduped = _deduplicate(all_papers)

        logger.info(
            "paper_service.search_complete",
            raw_count=len(all_papers),
            dedup_count=len(deduped),
        )
        return deduped

    # ── CRUD ────────────────────────────────────────────────────────

    @staticmethod
    async def get_paper(paper_id: str) -> Paper:
        """Get a single paper by ID.

        Raises:
            NotFoundError: If the paper does not exist.
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Paper).where(Paper.id == paper_id)
            )
            paper = result.scalar_one_or_none()
            if paper is None:
                raise NotFoundError(f"Paper {paper_id} not found")
            return paper

    @staticmethod
    async def list_papers(
        project_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Paper]:
        """List papers belonging to a project with pagination."""
        async with get_async_session() as session:
            stmt = (
                select(Paper)
                .where(Paper.project_id == project_id)
                .order_by(Paper.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def save_papers(
        project_id: str,
        papers: list[dict[str, Any]],
    ) -> list[Paper]:
        """Persist a list of paper metadata dicts to the database.

        Performs deduplication against papers already in the DB for this
        project (by DOI) before inserting.

        Args:
            project_id: UUID of the owning project.
            papers: List of normalised paper metadata dicts.

        Returns:
            List of newly created ``Paper`` ORM instances.
        """
        async with get_async_session() as session:
            # Load existing DOIs for this project to avoid duplicates
            existing_result = await session.execute(
                select(Paper.doi).where(
                    Paper.project_id == project_id,
                    Paper.doi.isnot(None),
                    Paper.doi != "",
                )
            )
            existing_dois: set[str] = {
                row[0].lower() for row in existing_result.all() if row[0]
            }

            created: list[Paper] = []
            for p in papers:
                doi = (p.get("doi") or "").strip().lower()
                if doi and doi in existing_dois:
                    continue

                paper = Paper(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=p.get("title", ""),
                    authors=p.get("authors", []),
                    abstract=p.get("abstract", ""),
                    year=p.get("year"),
                    doi=p.get("doi") or None,
                    source=p.get("source", "unknown"),
                    citation_count=p.get("citation_count", 0),
                    url=p.get("url", ""),
                    metadata_=p,
                    created_at=_dt.datetime.now(_dt.timezone.utc),
                )
                session.add(paper)
                created.append(paper)

                if doi:
                    existing_dois.add(doi)

            await session.commit()

            # Refresh all created papers to populate server defaults
            for paper in created:
                await session.refresh(paper)

            logger.info(
                "paper_service.saved",
                project_id=project_id,
                saved_count=len(created),
                skipped_duplicates=len(papers) - len(created),
            )
            return created


# ── Source search helpers (private) ─────────────────────────────────────


async def _search_arxiv(query: str, max_results: int) -> list[dict[str, Any]]:
    try:
        client = ArxivClient()
        raw = await client.search(query=query, max_results=max_results)
        return [
            {
                "title": p.get("title", ""),
                "authors": p.get("authors", []),
                "abstract": p.get("abstract", ""),
                "year": p.get("year") or (p.get("published", "") or "")[:4] or None,
                "doi": p.get("doi"),
                "source": "arxiv",
                "citation_count": p.get("citation_count", 0),
                "url": p.get("url", ""),
            }
            for p in raw
        ]
    except Exception as exc:
        logger.error("paper_service.arxiv_error", error=str(exc))
        return []


async def _search_semantic_scholar(
    query: str, max_results: int
) -> list[dict[str, Any]]:
    try:
        client = SemanticScholarClient()
        raw = await client.search(query=query, limit=max_results)
        return [
            {
                "title": p.get("title", ""),
                "authors": [
                    a.get("name", a) if isinstance(a, dict) else str(a)
                    for a in p.get("authors", [])
                ],
                "abstract": p.get("abstract", ""),
                "year": p.get("year"),
                "doi": p.get("externalIds", {}).get("DOI") or p.get("doi"),
                "source": "semantic_scholar",
                "citation_count": p.get("citationCount", 0),
                "url": p.get("url", ""),
            }
            for p in raw
        ]
    except Exception as exc:
        logger.error("paper_service.semantic_scholar_error", error=str(exc))
        return []


async def _search_crossref(query: str, max_results: int) -> list[dict[str, Any]]:
    try:
        client = CrossRefClient()
        raw = await client.search(query=query, rows=max_results)
        results: list[dict[str, Any]] = []
        for w in raw:
            title_raw = w.get("title", [""])
            title = title_raw[0] if isinstance(title_raw, list) else str(title_raw)
            issued = w.get("issued", {})
            date_parts = issued.get("date-parts", [[None]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            results.append(
                {
                    "title": title,
                    "authors": [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in w.get("author", [])
                    ],
                    "abstract": w.get("abstract", ""),
                    "year": year,
                    "doi": w.get("DOI", ""),
                    "source": "crossref",
                    "citation_count": w.get("is-referenced-by-count", 0),
                    "url": w.get("URL", ""),
                }
            )
        return results
    except Exception as exc:
        logger.error("paper_service.crossref_error", error=str(exc))
        return []
