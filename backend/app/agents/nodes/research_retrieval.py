"""Research retrieval node for the LangGraph workflow.

This node is responsible for:
1.  Formulating multiple diverse search queries from the research topic.
2.  Querying arXiv, Semantic Scholar, and CrossRef **in parallel**.
3.  Deduplicating results by DOI / normalised title.
4.  Ranking papers by citation count × relevance.
5.  Indexing papers into the Pinecone vector store via the RAG pipeline.
6.  Publishing agent events via the EventBus.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import hashlib
import json
import re
from typing import Any

from app.agents.state import ResearchState
from app.core.events import EventBus, AgentEvent
from app.integrations.arxiv_client import ArxivClient
from app.integrations.semantic_scholar_client import SemanticScholarClient
from app.integrations.crossref_client import CrossRefClient
from app.rag.embeddings import EmbeddingGenerator
from app.rag.vectorstore import VectorStore
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────

_STOP_WORDS = frozenset(
    {"a", "an", "the", "of", "and", "in", "to", "for", "on", "with", "is", "at", "by"}
)


def _normalise_title(title: str) -> str:
    """Lower-case, strip punctuation and stop-words for dedup matching."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    tokens = [t for t in title.split() if t not in _STOP_WORDS]
    return " ".join(tokens)


def _title_hash(title: str) -> str:
    return hashlib.md5(_normalise_title(title).encode()).hexdigest()


def _generate_queries(topic: str) -> list[str]:
    """Generate 3-5 diverse search query variants from a topic string.

    We apply simple heuristic transformations so the retrieval node can
    work even without an LLM call.
    """
    queries: list[str] = [topic]

    # Broader variant
    broad = re.sub(r"\b(using|via|with|based on)\b", "", topic, flags=re.I).strip()
    if broad and broad != topic:
        queries.append(broad)

    # More specific: add "survey" / "review"
    queries.append(f"{topic} survey review")

    # Methodological variant
    queries.append(f"{topic} methods approaches techniques")

    # Recent advances
    queries.append(f"recent advances {topic}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        q_norm = q.lower().strip()
        if q_norm not in seen:
            seen.add(q_norm)
            unique.append(q)

    return unique[:5]


def _deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate papers by DOI first, then by normalised title hash."""
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict[str, Any]] = []

    for paper in papers:
        doi = (paper.get("doi") or "").strip().lower()
        t_hash = _title_hash(paper.get("title", ""))

        if doi and doi in seen_dois:
            continue
        if t_hash in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        seen_titles.add(t_hash)
        unique.append(paper)

    return unique


def _rank_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank papers by citation count (descending), breaking ties by year."""
    return sorted(
        papers,
        key=lambda p: (
            -(p.get("citation_count") or 0),
            -(p.get("year") or 0),
        ),
    )


# ── Source search helpers ───────────────────────────────────────────────


async def _search_arxiv(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search arXiv, returning normalised paper dicts."""
    try:
        client = ArxivClient()
        raw = await client.search(query=query, max_results=max_results)
        results: list[dict[str, Any]] = []
        for p in raw:
            results.append(
                {
                    "title": p.title,
                    "authors": p.authors,
                    "abstract": p.abstract,
                    "year": p.published.year if p.published else None,
                    "doi": p.doi,
                    "arxiv_id": p.id,
                    "source": "arxiv",
                    "citation_count": 0,
                    "url": p.pdf_url,
                }
            )
        return results
    except Exception as exc:
        logger.error("research_retrieval.arxiv_error", error=str(exc), query=query)
        return []


async def _search_semantic_scholar(
    query: str, max_results: int
) -> list[dict[str, Any]]:
    """Search Semantic Scholar, returning normalised paper dicts."""
    try:
        client = SemanticScholarClient()
        raw = await client.search(query=query, limit=max_results)
        results: list[dict[str, Any]] = []
        for p in raw:
            results.append(
                {
                    "title": p.title,
                    "authors": [
                        a.get("name", a) if isinstance(a, dict) else str(a)
                        for a in p.authors
                    ],
                    "abstract": p.abstract or "",
                    "year": p.year,
                    "doi": p.doi or p.externalIds.get("DOI"),
                    "semantic_scholar_id": p.paperId,
                    "source": "semantic_scholar",
                    "citation_count": p.citationCount,
                    "url": p.url,
                }
            )
        return results
    except Exception as exc:
        logger.error(
            "research_retrieval.semantic_scholar_error",
            error=str(exc),
            query=query,
        )
        return []


async def _search_crossref(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search CrossRef, returning normalised paper dicts."""
    try:
        client = CrossRefClient()
        raw = await client.search(query=query, rows=max_results)
        results: list[dict[str, Any]] = []
        for w in raw:
            year = None
            if w.published_date:
                try:
                    year = int(w.published_date.split("-")[0])
                except (ValueError, IndexError):
                    pass

            results.append(
                {
                    "title": w.title,
                    "authors": [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in w.authors
                    ],
                    "abstract": w.abstract or "",
                    "year": year,
                    "doi": w.doi,
                    "source": "crossref",
                    "citation_count": w.is_referenced_by_count,
                    "url": w.url,
                }
            )
        return results
    except Exception as exc:
        logger.error(
            "research_retrieval.crossref_error", error=str(exc), query=query
        )
        return []


# ── Embedding helper ────────────────────────────────────────────────────


async def _index_papers(
    papers: list[dict[str, Any]], project_id: str
) -> bool:
    """Embed and upsert papers into the vector store.

    Returns ``True`` on success, ``False`` on failure.
    """
    if not papers:
        return True

    try:
        embedder = EmbeddingGenerator()
        store = VectorStore()

        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for paper in papers:
            # Combine title + abstract for embedding
            text = f"{paper.get('title', '')}\n\n{paper.get('abstract', '')}"
            texts.append(text)
            metadatas.append(
                {
                    "paper_title": paper.get("title", ""),
                    "doi": paper.get("doi", ""),
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "source": paper.get("source", ""),
                    "project_id": project_id,
                }
            )

        vectors = await embedder.generate(texts)
        await store.upsert(
            vectors=vectors,
            texts=texts,
            metadatas=metadatas,
            namespace=project_id,
        )

        logger.info(
            "research_retrieval.indexed_papers",
            count=len(papers),
            project_id=project_id,
        )
        return True

    except Exception as exc:
        logger.error(
            "research_retrieval.index_error",
            error=str(exc),
            project_id=project_id,
        )
        return False


# ── Main node function ──────────────────────────────────────────────────


async def research_retrieval_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: retrieve and index academic papers.

    Args:
        state: The current workflow state.

    Returns:
        A dict of state updates containing ``retrieved_papers``,
        ``paper_embeddings_stored``, ``current_agent``, ``agent_history``,
        and ``status``.
    """
    topic: str = state.get("topic", "")
    project_id: str = state.get("project_id", "")
    start_time = _dt.datetime.now(_dt.timezone.utc)

    logger.info(
        "research_retrieval.start",
        topic=topic,
        project_id=project_id,
    )

    # Publish start event
    try:
        event_bus = EventBus()
        await event_bus.publish(
            AgentEvent(
                agent_name="research_retrieval",
                event_type="started",
                project_id=project_id,
                data={"topic": topic},
            )
        )
    except Exception:
        logger.warning("research_retrieval.event_publish_failed")

    errors: list[dict[str, Any]] = []

    # 1. Generate search queries
    queries = _generate_queries(topic)
    logger.info("research_retrieval.queries", queries=queries)

    # 2. Search all sources in parallel for each query
    per_query_limit = 15
    search_coros: list[Any] = []
    for q in queries:
        search_coros.append(_search_arxiv(q, per_query_limit))
        search_coros.append(_search_semantic_scholar(q, per_query_limit))
        search_coros.append(_search_crossref(q, per_query_limit))

    all_results = await asyncio.gather(*search_coros, return_exceptions=True)

    # Flatten, skipping exceptions
    all_papers: list[dict[str, Any]] = []
    for result in all_results:
        if isinstance(result, BaseException):
            errors.append(
                {
                    "agent": "research_retrieval",
                    "error": str(result),
                    "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                }
            )
            continue
        if isinstance(result, list):
            all_papers.extend(result)

    logger.info(
        "research_retrieval.raw_count",
        raw_count=len(all_papers),
    )

    # 3. Deduplicate
    unique_papers = _deduplicate_papers(all_papers)
    logger.info(
        "research_retrieval.dedup_count",
        dedup_count=len(unique_papers),
    )

    # 4. Rank
    ranked_papers = _rank_papers(unique_papers)

    # 5. Index into vector store
    embeddings_stored = await _index_papers(ranked_papers, project_id)

    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start_time).total_seconds()

    # Publish completion event
    try:
        event_bus = EventBus()
        await event_bus.publish(
            AgentEvent(
                agent_name="research_retrieval",
                event_type="completed",
                project_id=project_id,
                data={
                    "paper_count": len(ranked_papers),
                    "embeddings_stored": embeddings_stored,
                    "elapsed_seconds": elapsed,
                },
            )
        )
    except Exception:
        logger.warning("research_retrieval.event_publish_failed")

    logger.info(
        "research_retrieval.complete",
        paper_count=len(ranked_papers),
        embeddings_stored=embeddings_stored,
        elapsed_seconds=elapsed,
    )

    return {
        "retrieved_papers": ranked_papers,
        "paper_embeddings_stored": embeddings_stored,
        "current_agent": "research_retrieval",
        "agent_history": [
            {
                "agent": "research_retrieval",
                "status": "completed",
                "paper_count": len(ranked_papers),
                "queries_used": queries,
                "elapsed_seconds": elapsed,
                "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            }
        ],
        "errors": errors,
        "status": "papers_retrieved",
    }
