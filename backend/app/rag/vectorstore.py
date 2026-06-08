"""Pinecone vector-store operations for the ResearchOS RAG pipeline.

Wraps :class:`~app.integrations.pinecone_client.PineconeManager` with
higher-level operations for indexing papers and searching by project
scope.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import VectorStoreError
from app.integrations.pinecone_client import PineconeManager, QueryResult
from app.rag.chunking import TextChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single search result from the vector store.

    Attributes:
        chunk_text: The text of the matched chunk.
        score: Cosine-similarity score (0–1).
        paper_id: Identifier of the source paper.
        doi: Digital Object Identifier (if available).
        title: Paper title.
        section: Section name the chunk belongs to.
        chunk_index: Index of the chunk within the paper.
    """

    chunk_text: str
    score: float
    paper_id: str = ""
    doi: str = ""
    title: str = ""
    section: str = ""
    chunk_index: int = 0


class VectorStore:
    """High-level vector store backed by Pinecone.

    Usage::

        vs = VectorStore()
        await vs.index_paper("paper-123", chunks, embeddings, metadata)
        results = await vs.search(query_vec, project_id="proj-1")
    """

    def __init__(self, pinecone: PineconeManager | None = None) -> None:
        self._pinecone = pinecone or PineconeManager()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def index_paper(
        self,
        paper_id: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Index all chunks of a paper into Pinecone.

        Args:
            paper_id: Unique paper identifier.
            chunks: Text chunks produced by the chunker.
            embeddings: Corresponding embedding vectors (same order and
                length as *chunks*).
            metadata: Paper-level metadata merged into each vector's
                metadata (e.g. title, doi, authors, project_id).

        Returns:
            Number of vectors successfully upserted.

        Raises:
            VectorStoreError: If chunk/embedding counts don't match or
                upsert fails.
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunk count ({len(chunks)}) != embedding count "
                f"({len(embeddings)})"
            )

        metadata = metadata or {}

        vectors: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings):
            vector_id = f"{paper_id}_{chunk.chunk_index}_{uuid.uuid4().hex[:8]}"
            vec_metadata = {
                **metadata,
                "paper_id": paper_id,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section or "",
                "chunk_text": chunk.text[:1000],  # Pinecone metadata limit
                "token_count": chunk.token_count,
            }
            # Merge chunk-level metadata.
            for k, v in chunk.metadata.items():
                if k not in vec_metadata:
                    vec_metadata[k] = v

            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": vec_metadata,
                }
            )

        count = await self._pinecone.upsert_vectors(vectors)
        logger.info(
            "vectorstore.paper_indexed",
            paper_id=paper_id,
            chunks=len(chunks),
            indexed=count,
        )
        return count

    async def index_chunks(
        self,
        chunks_with_embeddings: list[dict[str, Any]],
    ) -> int:
        """Index pre-assembled chunk+embedding dicts.

        Each item must contain:
        - ``id`` (str)
        - ``values`` (list[float])
        - ``metadata`` (dict)

        Args:
            chunks_with_embeddings: List of vector dicts.

        Returns:
            Number of vectors upserted.
        """
        if not chunks_with_embeddings:
            return 0
        count = await self._pinecone.upsert_vectors(chunks_with_embeddings)
        logger.info("vectorstore.chunks_indexed", count=count)
        return count

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query_embedding: list[float],
        project_id: str | None = None,
        top_k: int = 10,
        section_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search the vector store for chunks similar to *query_embedding*.

        Args:
            query_embedding: The query vector.
            project_id: Optional project scope filter.
            top_k: Maximum results to return.
            section_filter: Optional section name filter (e.g.
                ``"methods"``).

        Returns:
            Ranked list of :class:`SearchResult` objects.
        """
        metadata_filter: dict[str, Any] = {}
        if project_id:
            metadata_filter["project_id"] = {"$eq": project_id}
        if section_filter:
            metadata_filter["section"] = {"$eq": section_filter}

        query_results: list[QueryResult] = await self._pinecone.query(
            vector=query_embedding,
            top_k=top_k,
            filter=metadata_filter if metadata_filter else None,
            include_metadata=True,
        )

        results: list[SearchResult] = []
        for qr in query_results:
            meta = qr.metadata
            results.append(
                SearchResult(
                    chunk_text=meta.get("chunk_text", ""),
                    score=qr.score,
                    paper_id=meta.get("paper_id", ""),
                    doi=meta.get("doi", ""),
                    title=meta.get("title", ""),
                    section=meta.get("section", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                )
            )

        logger.debug(
            "vectorstore.search_complete",
            top_k=top_k,
            returned=len(results),
            project_id=project_id,
        )
        return results

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    async def delete_paper(self, paper_id: str) -> None:
        """Delete all vectors belonging to a paper.

        Args:
            paper_id: The paper identifier whose chunks should be
                removed.
        """
        await self._pinecone.delete_by_filter(
            {"paper_id": {"$eq": paper_id}}
        )
        logger.info("vectorstore.paper_deleted", paper_id=paper_id)
