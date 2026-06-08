"""LangChain tool wrapper for the ArxivClient integration.

Exposes ``search_arxiv`` as a LangChain ``@tool`` so it can be bound to
an LLM agent or called programmatically inside graph nodes.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.integrations.arxiv_client import ArxivClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def search_arxiv(
    query: str,
    max_results: int = 20,
) -> str:
    """Search arXiv for academic papers matching a query.

    Args:
        query: Natural-language search query (e.g. "transformer
            architectures for protein folding").
        max_results: Maximum number of results to return.  Capped at 50 to
            stay within arXiv rate limits.

    Returns:
        A JSON string containing a list of paper metadata dicts.  Each dict
        includes ``title``, ``authors``, ``abstract``, ``arxiv_id``,
        ``published``, ``updated``, ``doi``, ``categories``, ``pdf_url``,
        and ``citation_count`` (if available).
    """
    max_results = min(max_results, 50)

    logger.info(
        "tool.search_arxiv",
        query=query,
        max_results=max_results,
    )

    try:
        client = ArxivClient()
        papers: list[dict[str, Any]] = await client.search(
            query=query,
            max_results=max_results,
        )

        # Normalise output so downstream consumers always see the same keys
        normalised: list[dict[str, Any]] = []
        for paper in papers:
            normalised.append(
                {
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "abstract": paper.get("abstract", ""),
                    "arxiv_id": paper.get("arxiv_id") or paper.get("id", ""),
                    "year": paper.get("year") or paper.get("published", "")[:4],
                    "doi": paper.get("doi"),
                    "source": "arxiv",
                    "categories": paper.get("categories", []),
                    "pdf_url": paper.get("pdf_url", ""),
                    "citation_count": paper.get("citation_count", 0),
                    "url": paper.get("url", ""),
                }
            )

        logger.info(
            "tool.search_arxiv.success",
            result_count=len(normalised),
        )
        return json.dumps(normalised, ensure_ascii=False)

    except Exception as exc:
        logger.error("tool.search_arxiv.error", error=str(exc))
        return json.dumps({"error": str(exc)})
