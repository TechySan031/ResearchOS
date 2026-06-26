"""Embedding generation wrapper using BAAI/bge-large-en-v1.5.

Loads the ``sentence-transformers`` model **once** via a singleton
pattern and exposes an async interface by running the synchronous
encode calls in ``asyncio.to_thread()``.

For **query** embeddings the BGE instruction prefix is automatically
prepended:  ``"Represent this sentence for searching relevant passages: "``.
For **document** embeddings no prefix is added.
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from app.config import get_settings
from app.core.exceptions import EmbeddingError
from app.utils.logging import get_logger

logger = get_logger(__name__)

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingGenerator:
    """Singleton embedding generator backed by ``sentence-transformers``.

    Usage::

        gen = EmbeddingGenerator()
        vecs = await gen.generate(["hello world", "foo bar"])
        qvec = await gen.generate_query("What is attention?")
    """

    _instance: EmbeddingGenerator | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> EmbeddingGenerator:  # noqa: D102
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:  # type: ignore[attr-defined]
            return
        self._initialized = True
        self._model: Any = None
        self._model_name: str = ""
        self._batch_size: int = 32
        self._dimension: int = 1024

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    async def _ensure_model(self) -> None:
        """Load the sentence-transformer model if not already loaded."""
        if self._model is not None:
            return

        async with self._lock:
            if self._model is not None:
                return

            settings = get_settings()
            self._model_name = settings.embedding_model or "BAAI/bge-large-en-v1.5"
            device = settings.embedding_device or "cpu"
            self._dimension = int(settings.embedding_dimension or 1024)

            import time
            logger.info(
                "embeddings.loading_model",
                model=self._model_name,
                device=device,
            )
            start_time = time.perf_counter()

            try:
                from sentence_transformers import SentenceTransformer

                self._model = await asyncio.to_thread(
                    SentenceTransformer,
                    self._model_name,
                    device=device,
                )
                duration = time.perf_counter() - start_time
                logger.info(
                    "embeddings.model_loaded",
                    model=self._model_name,
                    dimension=self._dimension,
                    duration_seconds=round(duration, 2),
                )
            except Exception as exc:
                logger.error(
                    "embeddings.model_load_failed",
                    model=self._model_name,
                    error=str(exc),
                )
                raise EmbeddingError(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                ) from exc

    # ------------------------------------------------------------------
    # Internal encode
    # ------------------------------------------------------------------

    def _encode_sync(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[list[float]]:
        """Synchronous encode — called from a worker thread."""
        embeddings: np.ndarray = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        texts: list[str],
        *,
        normalize: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for a list of **document** texts.

        No instruction prefix is prepended — use :meth:`generate_query`
        for query embeddings.

        Args:
            texts: List of texts to embed.
            normalize: L2-normalise the output vectors (default
                ``True``).

        Returns:
            List of embedding vectors (each a ``list[float]`` of length
            ``EMBEDDING_DIMENSION``).

        Raises:
            EmbeddingError: On model or encoding failure.
        """
        if not texts:
            return []

        await self._ensure_model()

        try:
            embeddings = await asyncio.to_thread(
                self._encode_sync, texts, normalize
            )
            logger.debug(
                "embeddings.generated",
                count=len(embeddings),
                dim=len(embeddings[0]) if embeddings else 0,
            )
            return embeddings
        except Exception as exc:
            logger.error("embeddings.generate_failed", error=str(exc))
            raise EmbeddingError(
                f"Embedding generation failed: {exc}"
            ) from exc

    async def generate_single(
        self,
        text: str,
        *,
        normalize: bool = True,
    ) -> list[float]:
        """Generate an embedding for a single **document** text.

        Convenience wrapper around :meth:`generate`.
        """
        results = await self.generate([text], normalize=normalize)
        return results[0]

    async def generate_query(
        self,
        query: str,
        *,
        normalize: bool = True,
    ) -> list[float]:
        """Generate an embedding for a **query** text.

        The BGE instruction prefix is automatically prepended.

        Args:
            query: The search query.
            normalize: L2-normalise the output vector.

        Returns:
            A single embedding vector.
        """
        prefixed = f"{_BGE_QUERY_PREFIX}{query}"
        results = await self.generate([prefixed], normalize=normalize)
        return results[0]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Name of the loaded model."""
        return self._model_name
