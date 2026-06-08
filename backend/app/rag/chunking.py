"""Semantic text chunking for the ResearchOS RAG pipeline.

Supports three strategies:

- **SECTION_AWARE** — splits on detected academic-paper sections,
  falling back to recursive splitting within large sections.
- **RECURSIVE** — character/token-level splitting that respects
  sentence boundaries with configurable chunk size and overlap.
- **PARAGRAPH** — splits on double-newline paragraph boundaries.

Token counting is performed with ``tiktoken`` (``cl100k_base``
encoding, used by GPT-4 / text-embedding-ada-002).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import tiktoken

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Sentence-boundary regex — handles abbreviations and decimals
# reasonably well while splitting on ". ", "? ", "! ".
_SENTENCE_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z\"\'\(])"
)

# Tiktoken encoding used for token counting.
_ENCODING_NAME = "cl100k_base"
_encoder: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    """Lazily load the tiktoken encoder (singleton)."""
    global _encoder  # noqa: PLW0603
    if _encoder is None:
        _encoder = tiktoken.get_encoding(_ENCODING_NAME)
    return _encoder


def _count_tokens(text: str) -> int:
    """Count the number of tokens in *text*."""
    return len(_get_encoder().encode(text))


# -------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    SECTION_AWARE = "section_aware"
    RECURSIVE = "recursive"
    PARAGRAPH = "paragraph"


@dataclass(slots=True)
class TextChunk:
    """A single chunk of text produced by the chunker.

    Attributes:
        text: The chunk body.
        chunk_index: Zero-based index of this chunk within the
            document.
        section: The section name (if known), e.g. ``"introduction"``.
        metadata: Arbitrary metadata propagated from the source
            document plus chunking-specific keys.
        token_count: Number of tokens (``cl100k_base``).
    """

    text: str
    chunk_index: int
    section: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int = 0


# -------------------------------------------------------------------
# Chunker
# -------------------------------------------------------------------


class TextChunker:
    """Configurable text chunker.

    Args:
        chunk_size: Target chunk size in **tokens** (used by
            ``RECURSIVE`` and as a fallback for ``SECTION_AWARE``).
        chunk_overlap: Number of overlapping tokens between consecutive
            chunks (``RECURSIVE`` only).
        min_chunk_size: Minimum chunk size in tokens — chunks smaller
            than this are merged with their neighbour.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 30,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    # ------------------------------------------------------------------
    # Public dispatch
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        metadata: dict[str, Any] | None = None,
        sections: dict[str, str] | None = None,
    ) -> list[TextChunk]:
        """Chunk *text* using the specified *strategy*.

        Args:
            text: The full document text.
            strategy: Chunking strategy to use.
            metadata: Base metadata attached to every chunk.
            sections: Pre-detected section dict (required for
                ``SECTION_AWARE``).

        Returns:
            Ordered list of :class:`TextChunk` objects.
        """
        metadata = metadata or {}

        if strategy == ChunkingStrategy.SECTION_AWARE and sections:
            chunks = self.chunk_by_sections(text, sections, metadata)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self.chunk_by_paragraphs(text, metadata)
        else:
            chunks = self.chunk_recursive(text, self.chunk_size, self.chunk_overlap, metadata)

        logger.info(
            "chunker.complete",
            strategy=strategy.value,
            num_chunks=len(chunks),
            total_tokens=sum(c.token_count for c in chunks),
        )
        return chunks

    # ------------------------------------------------------------------
    # Section-aware chunking
    # ------------------------------------------------------------------

    def chunk_by_sections(
        self,
        text: str,
        sections: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Chunk by sections, recursively splitting large sections.

        Args:
            text: Full document text (used as fallback if sections is
                empty).
            sections: Mapping of section name → text.
            metadata: Base metadata for each chunk.

        Returns:
            Ordered list of :class:`TextChunk`.
        """
        metadata = metadata or {}
        all_chunks: list[TextChunk] = []
        index = 0

        if not sections:
            return self.chunk_recursive(text, self.chunk_size, self.chunk_overlap, metadata)

        for section_name, section_text in sections.items():
            section_text = section_text.strip()
            if not section_text:
                continue

            token_count = _count_tokens(section_text)

            if token_count <= self.chunk_size:
                # Section fits in a single chunk.
                all_chunks.append(
                    TextChunk(
                        text=section_text,
                        chunk_index=index,
                        section=section_name,
                        metadata={**metadata, "section": section_name},
                        token_count=token_count,
                    )
                )
                index += 1
            else:
                # Section is too large — recursively split.
                sub_chunks = self.chunk_recursive(
                    section_text,
                    self.chunk_size,
                    self.chunk_overlap,
                    {**metadata, "section": section_name},
                )
                for sc in sub_chunks:
                    sc.chunk_index = index
                    sc.section = section_name
                    index += 1
                all_chunks.extend(sub_chunks)

        return all_chunks

    # ------------------------------------------------------------------
    # Recursive chunking
    # ------------------------------------------------------------------

    def chunk_recursive(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split *text* into token-sized chunks respecting sentence boundaries.

        The algorithm:

        1. Split the text into sentences.
        2. Accumulate sentences into a buffer until adding the next
           sentence would exceed ``chunk_size`` tokens.
        3. Emit the buffer as a chunk and start a new buffer that
           overlaps with the tail of the previous chunk (by
           ``overlap`` tokens worth of trailing sentences).

        Args:
            text: Input text.
            chunk_size: Maximum tokens per chunk.
            overlap: Overlap in tokens between consecutive chunks.
            metadata: Base metadata.

        Returns:
            Ordered list of :class:`TextChunk`.
        """
        metadata = metadata or {}
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        chunks: list[TextChunk] = []
        index = 0
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sent_tokens = _count_tokens(sentence)

            # If a single sentence exceeds chunk_size, force it as its
            # own chunk (we never split mid-sentence).
            if sent_tokens > chunk_size:
                # Flush current buffer first.
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(
                        TextChunk(
                            text=chunk_text,
                            chunk_index=index,
                            metadata=dict(metadata),
                            token_count=_count_tokens(chunk_text),
                        )
                    )
                    index += 1

                chunks.append(
                    TextChunk(
                        text=sentence,
                        chunk_index=index,
                        metadata=dict(metadata),
                        token_count=sent_tokens,
                    )
                )
                index += 1
                current_sentences = []
                current_tokens = 0
                continue

            if current_tokens + sent_tokens > chunk_size and current_sentences:
                # Emit current chunk.
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=index,
                        metadata=dict(metadata),
                        token_count=_count_tokens(chunk_text),
                    )
                )
                index += 1

                # Build overlap from trailing sentences.
                overlap_sentences: list[str] = []
                overlap_tokens = 0
                for prev_sent in reversed(current_sentences):
                    prev_tokens = _count_tokens(prev_sent)
                    if overlap_tokens + prev_tokens > overlap:
                        break
                    overlap_sentences.insert(0, prev_sent)
                    overlap_tokens += prev_tokens

                current_sentences = overlap_sentences
                current_tokens = overlap_tokens

            current_sentences.append(sentence)
            current_tokens += sent_tokens

        # Flush remaining sentences.
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            tc = _count_tokens(chunk_text)
            if tc >= self.min_chunk_size or not chunks:
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        chunk_index=index,
                        metadata=dict(metadata),
                        token_count=tc,
                    )
                )
            elif chunks:
                # Merge small trailing chunk with the previous one.
                prev = chunks[-1]
                merged = prev.text + " " + chunk_text
                chunks[-1] = TextChunk(
                    text=merged,
                    chunk_index=prev.chunk_index,
                    section=prev.section,
                    metadata=prev.metadata,
                    token_count=_count_tokens(merged),
                )

        return chunks

    # ------------------------------------------------------------------
    # Paragraph chunking
    # ------------------------------------------------------------------

    def chunk_by_paragraphs(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split *text* on paragraph boundaries (double newlines).

        Very small paragraphs are merged with the next paragraph.

        Args:
            text: Input text.
            metadata: Base metadata.

        Returns:
            Ordered list of :class:`TextChunk`.
        """
        metadata = metadata or {}
        raw_paragraphs = re.split(r"\n\s*\n", text)
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

        if not paragraphs:
            return []

        chunks: list[TextChunk] = []
        index = 0
        buffer = ""

        for para in paragraphs:
            candidate = (buffer + "\n\n" + para).strip() if buffer else para
            tc = _count_tokens(candidate)

            if tc > self.chunk_size and buffer:
                # Emit the buffer and start fresh with current paragraph.
                buf_tc = _count_tokens(buffer)
                chunks.append(
                    TextChunk(
                        text=buffer,
                        chunk_index=index,
                        metadata=dict(metadata),
                        token_count=buf_tc,
                    )
                )
                index += 1
                buffer = para
            else:
                buffer = candidate

        # Flush
        if buffer:
            tc = _count_tokens(buffer)
            if tc >= self.min_chunk_size or not chunks:
                chunks.append(
                    TextChunk(
                        text=buffer,
                        chunk_index=index,
                        metadata=dict(metadata),
                        token_count=tc,
                    )
                )
            elif chunks:
                prev = chunks[-1]
                merged = prev.text + "\n\n" + buffer
                chunks[-1] = TextChunk(
                    text=merged,
                    chunk_index=prev.chunk_index,
                    section=prev.section,
                    metadata=prev.metadata,
                    token_count=_count_tokens(merged),
                )

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split *text* into sentences, preserving non-trivial content."""
        sentences = _SENTENCE_RE.split(text)
        return [s.strip() for s in sentences if s.strip()]
