"""LangChain tool wrappers for the Semantic Scholar integration.

Exposes ``search_semantic_scholar`` and ``get_paper_details`` as LangChain
``@tool`` functions.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.integrations.semantic_scholar_client import SemanticScholarClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def search_semantic_scholar(
    query: str,
    max_results: int = 20,
) -> str:
    """Search Semantic Scholar for academic papers.

    Args:
        query: Natural-language search query.
        max_results: Maximum number of results (capped at 100).

    Returns:
        JSON string of paper metadata dicts with keys ``title``,
        ``authors``, ``abstract``, ``year``, ``doi``,
        ``citation_count``, ``source``, and ``url``.
    """
    max_results = min(max_results, 100)

    logger.info(
        "tool.search_semantic_scholar",
        query=query,
        max_results=max_results,
    )

    try:
        client = SemanticScholarClient()
        papers: list[dict[str, Any]] = await client.search(
            query=query,
            limit=max_results,
        )

        normalised: list[dict[str, Any]] = []
        for paper in papers:
            normalised.append(
                {
                    "title": paper.get("title", ""),
                    "authors": [
                        a.get("name", a) if isinstance(a, dict) else str(a)
                        for a in paper.get("authors", [])
                    ],
                    "abstract": paper.get("abstract", ""),
                    "year": paper.get("year"),
                    "doi": paper.get("externalIds", {}).get("DOI")
                    or paper.get("doi"),
                    "semantic_scholar_id": paper.get("paperId", ""),
                    "source": "semantic_scholar",
                    "citation_count": paper.get("citationCount", 0),
                    "url": paper.get("url", ""),
                    "venue": paper.get("venue", ""),
                    "fields_of_study": paper.get("fieldsOfStudy", []),
                }
            )

        logger.info(
            "tool.search_semantic_scholar.success",
            result_count=len(normalised),
        )
        return json.dumps(normalised, ensure_ascii=False)

    except Exception as exc:
        logger.error("tool.search_semantic_scholar.error", error=str(exc))
        return json.dumps({"error": str(exc)})


@tool
async def get_paper_details(paper_id: str) -> str:
    """Retrieve full metadata for a single Semantic Scholar paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI, or arXiv ID.

    Returns:
        JSON string with comprehensive paper metadata.
    """
    logger.info("tool.get_paper_details", paper_id=paper_id)

    try:
        client = SemanticScholarClient()
        details: dict[str, Any] = await client.get_paper(paper_id=paper_id)

        result: dict[str, Any] = {
            "title": details.get("title", ""),
            "authors": [
                a.get("name", a) if isinstance(a, dict) else str(a)
                for a in details.get("authors", [])
            ],
            "abstract": details.get("abstract", ""),
            "year": details.get("year"),
            "doi": details.get("externalIds", {}).get("DOI")
            or details.get("doi"),
            "citation_count": details.get("citationCount", 0),
            "references": [
                {
                    "title": ref.get("title", ""),
                    "doi": ref.get("externalIds", {}).get("DOI"),
                    "year": ref.get("year"),
                }
                for ref in (details.get("references") or [])[:50]
            ],
            "tldr": details.get("tldr", {}).get("text", ""),
            "venue": details.get("venue", ""),
            "url": details.get("url", ""),
        }

        logger.info("tool.get_paper_details.success", paper_id=paper_id)
        return json.dumps(result, ensure_ascii=False)

    except Exception as exc:
        logger.error("tool.get_paper_details.error", error=str(exc))
        return json.dumps({"error": str(exc)})
