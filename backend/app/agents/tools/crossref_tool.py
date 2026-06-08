"""LangChain tool wrappers for the CrossRef integration.

Exposes ``verify_doi`` and ``search_crossref`` as LangChain ``@tool``
functions for citation verification and bibliographic search.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.integrations.crossref_client import CrossRefClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def verify_doi(doi: str) -> str:
    """Verify that a DOI resolves to a valid CrossRef record.

    Args:
        doi: The DOI string to verify (e.g. ``"10.1038/s41586-023-06747-5"``).

    Returns:
        JSON string containing verification status, resolved metadata, or an
        error message.
    """
    logger.info("tool.verify_doi", doi=doi)

    try:
        client = CrossRefClient()
        record: dict[str, Any] = await client.get_work(doi=doi)

        result: dict[str, Any] = {
            "verified": True,
            "doi": doi,
            "title": record.get("title", [""])[0]
            if isinstance(record.get("title"), list)
            else record.get("title", ""),
            "authors": [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in record.get("author", [])
            ],
            "publisher": record.get("publisher", ""),
            "type": record.get("type", ""),
            "issued": record.get("issued", {}),
            "container_title": (
                record.get("container-title", [""])[0]
                if isinstance(record.get("container-title"), list)
                else record.get("container-title", "")
            ),
            "url": record.get("URL", ""),
        }

        logger.info("tool.verify_doi.success", doi=doi, verified=True)
        return json.dumps(result, ensure_ascii=False)

    except Exception as exc:
        logger.warning("tool.verify_doi.failed", doi=doi, error=str(exc))
        return json.dumps(
            {"verified": False, "doi": doi, "error": str(exc)}
        )


@tool
async def search_crossref(
    query: str,
    max_results: int = 20,
) -> str:
    """Search the CrossRef database for academic works.

    Args:
        query: Free-text bibliographic query.
        max_results: Maximum number of results (capped at 50).

    Returns:
        JSON string with a list of work metadata dicts.
    """
    max_results = min(max_results, 50)

    logger.info(
        "tool.search_crossref",
        query=query,
        max_results=max_results,
    )

    try:
        client = CrossRefClient()
        works: list[dict[str, Any]] = await client.search(
            query=query,
            rows=max_results,
        )

        normalised: list[dict[str, Any]] = []
        for work in works:
            title_raw = work.get("title", [""])
            title = title_raw[0] if isinstance(title_raw, list) else str(title_raw)

            container_raw = work.get("container-title", [""])
            container = (
                container_raw[0]
                if isinstance(container_raw, list)
                else str(container_raw)
            )

            # Extract year from issued date-parts
            issued = work.get("issued", {})
            date_parts = issued.get("date-parts", [[None]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None

            normalised.append(
                {
                    "title": title,
                    "authors": [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in work.get("author", [])
                    ],
                    "abstract": work.get("abstract", ""),
                    "year": year,
                    "doi": work.get("DOI", ""),
                    "source": "crossref",
                    "citation_count": work.get("is-referenced-by-count", 0),
                    "container_title": container,
                    "type": work.get("type", ""),
                    "url": work.get("URL", ""),
                }
            )

        logger.info(
            "tool.search_crossref.success",
            result_count=len(normalised),
        )
        return json.dumps(normalised, ensure_ascii=False)

    except Exception as exc:
        logger.error("tool.search_crossref.error", error=str(exc))
        return json.dumps({"error": str(exc)})
