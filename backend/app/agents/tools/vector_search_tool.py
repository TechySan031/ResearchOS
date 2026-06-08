"""LangChain tool wrapper for the RAG semantic retriever.

Exposes ``semantic_search`` as a LangChain ``@tool`` so agents can query
the Pinecone vector store for relevant paper chunks.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.rag.retriever import SemanticRetriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def semantic_search(
    query: str,
    project_id: str,
    top_k: int = 10,
) -> str:
    """Search the project's vector store for semantically similar chunks.

    This queries the Pinecone index via the SemanticRetriever to find the
    most relevant document sections for a given natural-language query.

    Args:
        query: The search query in natural language.
        project_id: The project whose indexed papers should be searched.
        top_k: Number of top results to return (default 10, max 50).

    Returns:
        JSON string with a list of result dicts, each containing
        ``text``, ``score``, ``metadata`` (paper title, DOI, section,
        etc.).
    """
    top_k = min(max(top_k, 1), 50)

    logger.info(
        "tool.semantic_search",
        query=query[:120],
        project_id=project_id,
        top_k=top_k,
    )

    try:
        retriever = SemanticRetriever()
        results: list[dict[str, Any]] = await retriever.search(
            query=query,
            project_id=project_id,
            top_k=top_k,
        )

        formatted: list[dict[str, Any]] = []
        for result in results:
            formatted.append(
                {
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "metadata": {
                        "paper_title": result.get("metadata", {}).get(
                            "paper_title", ""
                        ),
                        "doi": result.get("metadata", {}).get("doi", ""),
                        "section": result.get("metadata", {}).get("section", ""),
                        "authors": result.get("metadata", {}).get("authors", []),
                        "year": result.get("metadata", {}).get("year"),
                        "chunk_index": result.get("metadata", {}).get(
                            "chunk_index", 0
                        ),
                    },
                }
            )

        logger.info(
            "tool.semantic_search.success",
            result_count=len(formatted),
        )
        return json.dumps(formatted, ensure_ascii=False)

    except Exception as exc:
        logger.error("tool.semantic_search.error", error=str(exc))
        return json.dumps({"error": str(exc)})
