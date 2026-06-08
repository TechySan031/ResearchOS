"""Pinecone vector-database client wrapper.

Provides ``PineconeManager`` — a thin async wrapper around the
official Pinecone Python SDK (``pinecone-client >= 3.0``) with:

- Index creation / connection.
- Batched upsert of embedding vectors with metadata.
- Filtered vector queries.
- Deletion by metadata filter.
- Index statistics.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.core.exceptions import VectorStoreError
from app.utils.logging import get_logger

logger = get_logger(__name__)

_UPSERT_BATCH_SIZE = 100


@dataclass(frozen=True, slots=True)
class QueryResult:
    """Single result from a Pinecone vector query.

    Attributes:
        id: Vector identifier.
        score: Cosine similarity score (0–1).
        metadata: Arbitrary metadata dict stored alongside the vector.
    """

    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class PineconeManager:
    """Manages a single Pinecone index for ResearchOS embeddings.

    Instantiate once at application startup and call :meth:`init_index`
    before performing any operations.

    Usage::

        pm = PineconeManager()
        await pm.init_index()
        await pm.upsert_vectors([
            {"id": "v1", "values": [...], "metadata": {...}},
        ])
        results = await pm.query(query_vec, top_k=5)
    """

    def __init__(self) -> None:
        self._pc: Pinecone | None = None
        self._index: Any | None = None
        self._index_name: str = ""
        self._dimension: int = 1024

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def init_index(self) -> None:
        """Create or connect to the configured Pinecone index.

        Reads ``PINECONE_API_KEY``, ``PINECONE_INDEX_NAME``,
        ``PINECONE_ENVIRONMENT``, and ``EMBEDDING_DIMENSION`` from
        settings.

        Raises:
            VectorStoreError: On authentication or connection failure.
        """
        settings = get_settings()
        api_key: str = settings.pinecone_api_key
        self._index_name = settings.pinecone_index_name
        environment: str = settings.pinecone_environment
        self._dimension = settings.embedding_dimension

        try:
            self._pc = await asyncio.to_thread(Pinecone, api_key=api_key)

            # List existing indexes to decide whether to create.
            existing_indexes = await asyncio.to_thread(self._pc.list_indexes)
            index_names = [idx.name for idx in existing_indexes]

            if self._index_name not in index_names:
                logger.info(
                    "pinecone.creating_index",
                    name=self._index_name,
                    dimension=self._dimension,
                )
                await asyncio.to_thread(
                    self._pc.create_index,
                    name=self._index_name,
                    dimension=self._dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=environment,
                    ),
                )
                logger.info("pinecone.index_created", name=self._index_name)

            self._index = await asyncio.to_thread(
                self._pc.Index, self._index_name
            )
            logger.info("pinecone.connected", index=self._index_name)

        except Exception as exc:
            logger.error("pinecone.init_failed", error=str(exc))
            raise VectorStoreError(
                f"Failed to initialise Pinecone index: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _ensure_index(self) -> Any:
        """Return the index or raise if not initialised."""
        if self._index is None:
            raise VectorStoreError(
                "Pinecone index not initialised — call init_index() first"
            )
        return self._index

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    async def upsert_vectors(self, vectors: list[dict[str, Any]]) -> int:
        """Batch-upsert vectors into the index.

        Each item in *vectors* must have:
        - ``id`` (str): unique vector identifier.
        - ``values`` (list[float]): the embedding vector.
        - ``metadata`` (dict): arbitrary metadata.

        Vectors are upserted in batches of ``_UPSERT_BATCH_SIZE`` to
        stay within Pinecone payload limits.

        Args:
            vectors: List of vector dicts.

        Returns:
            Total number of vectors upserted.

        Raises:
            VectorStoreError: On upsert failure.
        """
        index = self._ensure_index()
        total_upserted = 0
        num_batches = math.ceil(len(vectors) / _UPSERT_BATCH_SIZE)

        for batch_idx in range(num_batches):
            start = batch_idx * _UPSERT_BATCH_SIZE
            end = start + _UPSERT_BATCH_SIZE
            batch = vectors[start:end]

            # Convert to list of tuples (id, values, metadata) accepted
            # by the SDK.
            records = [
                (v["id"], v["values"], v.get("metadata", {}))
                for v in batch
            ]

            try:
                await asyncio.to_thread(index.upsert, vectors=records)
                total_upserted += len(records)
                logger.debug(
                    "pinecone.upsert_batch",
                    batch=batch_idx + 1,
                    total_batches=num_batches,
                    count=len(records),
                )
            except Exception as exc:
                logger.error(
                    "pinecone.upsert_failed",
                    batch=batch_idx + 1,
                    error=str(exc),
                )
                raise VectorStoreError(
                    f"Pinecone upsert failed on batch {batch_idx + 1}: {exc}"
                ) from exc

        logger.info("pinecone.upsert_complete", total=total_upserted)
        return total_upserted

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(
        self,
        vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
        include_metadata: bool = True,
    ) -> list[QueryResult]:
        """Query the index for the nearest neighbours of *vector*.

        Args:
            vector: The query embedding.
            top_k: Number of results to return.
            filter: Optional Pinecone metadata filter dict.
            include_metadata: Whether to include metadata in results.

        Returns:
            Ranked list of :class:`QueryResult` objects.

        Raises:
            VectorStoreError: On query failure.
        """
        index = self._ensure_index()

        try:
            response = await asyncio.to_thread(
                index.query,
                vector=vector,
                top_k=top_k,
                filter=filter or {},
                include_metadata=include_metadata,
            )
        except Exception as exc:
            logger.error("pinecone.query_failed", error=str(exc))
            raise VectorStoreError(
                f"Pinecone query failed: {exc}"
            ) from exc

        results: list[QueryResult] = []
        for match in response.get("matches", []):
            results.append(
                QueryResult(
                    id=match["id"],
                    score=float(match.get("score", 0.0)),
                    metadata=match.get("metadata", {}),
                )
            )

        logger.debug("pinecone.query_complete", top_k=top_k, returned=len(results))
        return results

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_by_filter(self, filter: dict[str, Any]) -> None:
        """Delete vectors matching a metadata *filter*.

        Args:
            filter: Pinecone metadata filter dict (e.g.
                ``{"paper_id": {"$eq": "abc123"}}``).

        Raises:
            VectorStoreError: On deletion failure.
        """
        index = self._ensure_index()

        try:
            await asyncio.to_thread(
                index.delete, filter=filter
            )
            logger.info("pinecone.delete_by_filter", filter=filter)
        except Exception as exc:
            logger.error("pinecone.delete_failed", filter=filter, error=str(exc))
            raise VectorStoreError(
                f"Pinecone delete failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_index_stats(self) -> dict[str, Any]:
        """Return index statistics (vector count, dimension, etc.).

        Returns:
            Dictionary with keys like ``total_vector_count``,
            ``dimension``, and per-namespace breakdowns.

        Raises:
            VectorStoreError: On stats retrieval failure.
        """
        index = self._ensure_index()

        try:
            stats = await asyncio.to_thread(index.describe_index_stats)
            result = {
                "total_vector_count": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", self._dimension),
                "namespaces": stats.get("namespaces", {}),
                "index_fullness": stats.get("index_fullness", 0.0),
            }
            logger.info("pinecone.stats", **result)
            return result
        except Exception as exc:
            logger.error("pinecone.stats_failed", error=str(exc))
            raise VectorStoreError(
                f"Failed to retrieve Pinecone index stats: {exc}"
            ) from exc
