"""
ResearchOS — Semantic Retriever

Retrieval with score-based filtering, deduplication, and context
enrichment. Sits on top of VectorStore and EmbeddingGenerator to
provide a high-level retrieval interface for agents.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from app.rag.embeddings import EmbeddingGenerator
from app.rag.vectorstore import VectorStore
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with full metadata."""
    text: str
    score: float
    paper_id: str
    doi: str = ""
    title: str = ""
    authors: str = ""
    section: str = ""
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


class SemanticRetriever:
    """
    High-level semantic retrieval interface.

    Combines embedding generation, Pinecone vector search,
    score-based filtering, and deduplication into a single
    retrieve() call.
    """

    # BGE query instruction prefix for asymmetric retrieval
    QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    # Minimum similarity score to include in results
    MIN_SCORE_THRESHOLD = 0.5

    def __init__(
        self,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self._embedder = embedding_generator or EmbeddingGenerator()
        self._vectorstore = vector_store or VectorStore()

    async def retrieve(
        self,
        query: str,
        project_id: str,
        top_k: int = 10,
        section_filter: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Natural language search query.
            project_id: Project ID for tenant isolation.
            top_k: Maximum number of results to return.
            section_filter: Optional section name filter (e.g., "methods").
            min_score: Minimum similarity score (default: 0.5).

        Returns:
            List of RetrievalResult sorted by descending score.
        """
        threshold = min_score or self.MIN_SCORE_THRESHOLD

        logger.info(
            "retrieval_started",
            query_preview=query[:100],
            project_id=project_id,
            top_k=top_k,
            section_filter=section_filter,
        )

        # Generate query embedding with BGE instruction prefix
        prefixed_query = f"{self.QUERY_PREFIX}{query}"
        query_embedding = await self._embedder.generate_single(prefixed_query)

        # Search Pinecone
        search_results = await self._vectorstore.search(
            query_embedding=query_embedding,
            project_id=project_id,
            top_k=top_k * 2,  # Over-fetch for filtering
            section_filter=section_filter,
        )

        # Filter by score threshold
        filtered = [
            r for r in search_results
            if r.score >= threshold
        ]

        # Deduplicate by paper_id (keep highest score per paper)
        deduplicated = self._deduplicate_by_paper(filtered)

        # Convert to RetrievalResult
        results = []
        for sr in deduplicated[:top_k]:
            results.append(RetrievalResult(
                text=sr.chunk_text,
                score=sr.score,
                paper_id=sr.paper_id,
                doi=sr.doi,
                title=sr.title,
                section=sr.section,
                chunk_index=sr.chunk_index,
                metadata={"source": "pinecone"},
            ))

        logger.info(
            "retrieval_completed",
            query_preview=query[:80],
            total_raw=len(search_results),
            after_filter=len(filtered),
            after_dedup=len(results),
        )

        return results

    async def retrieve_with_context(
        self,
        query: str,
        project_id: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Retrieve results with extended context.

        Fetches neighboring chunks for each top result to provide
        more context around the matched passage.

        Args:
            query: Search query.
            project_id: Project ID for isolation.
            top_k: Number of results.

        Returns:
            Retrieval results with expanded text context.
        """
        results = await self.retrieve(
            query=query,
            project_id=project_id,
            top_k=top_k,
        )

        # For each result, try to fetch adjacent chunks for context
        enriched_results = []
        for result in results:
            # Fetch the previous and next chunks from the same paper
            context_chunks = await self._fetch_adjacent_chunks(
                paper_id=result.paper_id,
                chunk_index=result.chunk_index,
                project_id=project_id,
            )

            # Build extended text
            extended_parts = []
            if context_chunks.get("previous"):
                extended_parts.append(context_chunks["previous"])
            extended_parts.append(result.text)
            if context_chunks.get("next"):
                extended_parts.append(context_chunks["next"])

            enriched_result = RetrievalResult(
                text="\n\n".join(extended_parts),
                score=result.score,
                paper_id=result.paper_id,
                doi=result.doi,
                title=result.title,
                authors=result.authors,
                section=result.section,
                chunk_index=result.chunk_index,
                metadata={**result.metadata, "context_enriched": True},
            )
            enriched_results.append(enriched_result)

        return enriched_results

    async def multi_query_retrieve(
        self,
        queries: list[str],
        project_id: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """
        Retrieve using multiple query variants and merge results.

        Useful when a single query may not capture all relevant aspects.
        Results are merged by score with cross-query deduplication.

        Args:
            queries: List of query variants.
            project_id: Project ID.
            top_k: Max total results after merging.

        Returns:
            Merged and deduplicated results.
        """
        # Run all queries in parallel
        tasks = [
            self.retrieve(q, project_id, top_k=top_k)
            for q in queries
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge all results
        merged = []
        for result_set in all_results:
            if isinstance(result_set, Exception):
                logger.warning("multi_query_partial_failure", error=str(result_set))
                continue
            merged.extend(result_set)

        # Deduplicate across queries (by text content hash)
        seen_texts = set()
        unique = []
        for r in sorted(merged, key=lambda x: x.score, reverse=True):
            text_key = r.text[:200]  # Use first 200 chars as dedup key
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique.append(r)

        return unique[:top_k]

    def _deduplicate_by_paper(self, results) -> list:
        """
        Keep only the highest-scoring chunk per paper.

        For diverse results, we want at most one chunk per paper
        in the top results.
        """
        best_per_paper: dict[str, object] = {}
        for r in results:
            paper_key = r.paper_id
            if paper_key not in best_per_paper or r.score > best_per_paper[paper_key].score:
                best_per_paper[paper_key] = r

        # Sort by score descending
        return sorted(best_per_paper.values(), key=lambda x: x.score, reverse=True)

    async def _fetch_adjacent_chunks(
        self,
        paper_id: str,
        chunk_index: int,
        project_id: str,
    ) -> dict[str, str]:
        """
        Fetch previous and next chunks for context expansion.

        Returns dict with 'previous' and 'next' text if available.
        """
        context = {}

        for offset, key in [(-1, "previous"), (1, "next")]:
            target_index = chunk_index + offset
            if target_index < 0:
                continue

            try:
                # Search for the specific chunk by metadata filter
                results = await self._vectorstore.search(
                    query_embedding=[0.0] * 1024,  # Dummy — we filter by metadata
                    project_id=project_id,
                    top_k=1,
                    metadata_filter={
                        "paper_id": paper_id,
                        "chunk_index": target_index,
                    },
                )
                if results:
                    context[key] = results[0].chunk_text
            except Exception:
                # Adjacent chunk not found — skip gracefully
                pass

        return context
