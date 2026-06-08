"""Paper ingestion pipeline for the ResearchOS RAG system.

Handles extraction of text and metadata from:
- arXiv papers (via ``ArxivPaper`` objects).
- Local PDF files (using ``pdfplumber`` with ``PyMuPDF`` fallback).
- Raw text with caller-supplied metadata.

Section detection uses a curated set of regular expressions that
recognise common academic paper headings (Abstract, Introduction,
Methods / Methodology, Results, Discussion, Conclusion, References).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.exceptions import ExternalAPIError
from app.integrations.arxiv_client import ArxivPaper
from app.utils.logging import get_logger

logger = get_logger(__name__)

# -------------------------------------------------------------------
# Section-detection patterns
# -------------------------------------------------------------------

_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("abstract", re.compile(r"^(?:\d+[\.\)]\s*)?abstract\s*$", re.IGNORECASE | re.MULTILINE)),
    ("introduction", re.compile(r"^(?:\d+[\.\)]\s*)?introduction\s*$", re.IGNORECASE | re.MULTILINE)),
    ("related_work", re.compile(r"^(?:\d+[\.\)]\s*)?related\s+work\s*$", re.IGNORECASE | re.MULTILINE)),
    ("background", re.compile(r"^(?:\d+[\.\)]\s*)?background\s*$", re.IGNORECASE | re.MULTILINE)),
    ("methods", re.compile(r"^(?:\d+[\.\)]\s*)?(?:methods?|methodology|approach|experimental\s+setup)\s*$", re.IGNORECASE | re.MULTILINE)),
    ("results", re.compile(r"^(?:\d+[\.\)]\s*)?(?:results?|experiments?|evaluation)\s*$", re.IGNORECASE | re.MULTILINE)),
    ("discussion", re.compile(r"^(?:\d+[\.\)]\s*)?discussion\s*$", re.IGNORECASE | re.MULTILINE)),
    ("conclusion", re.compile(r"^(?:\d+[\.\)]\s*)?(?:conclusions?|summary|concluding\s+remarks)\s*$", re.IGNORECASE | re.MULTILINE)),
    ("references", re.compile(r"^(?:\d+[\.\)]\s*)?references\s*$", re.IGNORECASE | re.MULTILINE)),
    ("appendix", re.compile(r"^(?:[A-Z][\.\)]\s*)?(?:appendix|supplementary)\s*", re.IGNORECASE | re.MULTILINE)),
]


@dataclass(slots=True)
class IngestedPaper:
    """Container for an ingested paper's extracted text and metadata.

    Attributes:
        text: Full extracted text.
        metadata: Arbitrary metadata (title, authors, source, doi, …).
        sections: Mapping of normalised section names to their text
            content.  Empty if section detection fails.
        source: Origin identifier (``"arxiv"``, ``"pdf"``, ``"text"``).
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    source: str = ""


class PaperIngestor:
    """Extracts text, metadata, and sections from academic papers.

    All public methods are async-safe — CPU-bound PDF parsing is
    offloaded to a thread pool.
    """

    # ------------------------------------------------------------------
    # arXiv ingestion
    # ------------------------------------------------------------------

    async def ingest_from_arxiv(self, arxiv_paper: ArxivPaper) -> IngestedPaper:
        """Ingest an arXiv paper.

        The abstract is used as the main text body (since the full text
        requires PDF download and extraction).  If the full text is
        needed, download the PDF first and call :meth:`ingest_from_pdf`.

        Args:
            arxiv_paper: An :class:`ArxivPaper` instance.

        Returns:
            An :class:`IngestedPaper` with metadata populated from the
            arXiv record.
        """
        metadata: dict[str, Any] = {
            "title": arxiv_paper.title,
            "authors": arxiv_paper.authors,
            "arxiv_id": arxiv_paper.id,
            "doi": arxiv_paper.doi,
            "published": str(arxiv_paper.published),
            "updated": str(arxiv_paper.updated),
            "categories": arxiv_paper.categories,
            "pdf_url": arxiv_paper.pdf_url,
            "comment": arxiv_paper.comment,
        }

        # Build a lightweight body from the abstract.
        text = arxiv_paper.abstract or ""

        sections: dict[str, str] = {}
        if arxiv_paper.abstract:
            sections["abstract"] = arxiv_paper.abstract

        logger.info(
            "ingest.arxiv_complete",
            arxiv_id=arxiv_paper.id,
            title=arxiv_paper.title,
            text_len=len(text),
        )

        return IngestedPaper(
            text=text,
            metadata=metadata,
            sections=sections,
            source="arxiv",
        )

    # ------------------------------------------------------------------
    # PDF ingestion
    # ------------------------------------------------------------------

    async def ingest_from_pdf(self, file_path: str | Path) -> IngestedPaper:
        """Extract text and metadata from a PDF file.

        Uses ``pdfplumber`` as the primary extractor and falls back to
        ``PyMuPDF`` (``fitz``) when ``pdfplumber`` fails or yields
        empty text.

        Args:
            file_path: Path to the PDF file.

        Returns:
            An :class:`IngestedPaper` with extracted text and sections.

        Raises:
            ExternalAPIError: If the PDF cannot be read by either
                backend.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise ExternalAPIError(
                f"PDF file not found: {file_path}",
                service="pdf_ingest",
            )

        text = await asyncio.to_thread(self._extract_pdf_pdfplumber, file_path)

        if not text or len(text.strip()) < 100:
            logger.warning(
                "ingest.pdfplumber_fallback",
                path=str(file_path),
                pdfplumber_len=len(text) if text else 0,
            )
            text = await asyncio.to_thread(self._extract_pdf_pymupdf, file_path)

        if not text or len(text.strip()) < 50:
            raise ExternalAPIError(
                f"Could not extract meaningful text from PDF: {file_path}",
                service="pdf_ingest",
            )

        # Normalise whitespace.
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        metadata = self._extract_pdf_metadata(text, file_path)
        sections = self._detect_sections(text)

        logger.info(
            "ingest.pdf_complete",
            path=str(file_path),
            text_len=len(text),
            sections_found=list(sections.keys()),
        )

        return IngestedPaper(
            text=text,
            metadata=metadata,
            sections=sections,
            source="pdf",
        )

    @staticmethod
    def _extract_pdf_pdfplumber(file_path: Path) -> str:
        """Synchronous text extraction with *pdfplumber*."""
        try:
            import pdfplumber

            pages: list[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append(page_text)
            return "\n\n".join(pages)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ingest.pdfplumber_error",
                path=str(file_path),
                error=str(exc),
            )
            return ""

    @staticmethod
    def _extract_pdf_pymupdf(file_path: Path) -> str:
        """Synchronous text extraction with *PyMuPDF* (``fitz``)."""
        try:
            import fitz  # PyMuPDF

            pages: list[str] = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        pages.append(page_text)
            return "\n\n".join(pages)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ingest.pymupdf_error",
                path=str(file_path),
                error=str(exc),
            )
            return ""

    @staticmethod
    def _extract_pdf_metadata(text: str, file_path: Path) -> dict[str, Any]:
        """Heuristic metadata extraction from the first page of text.

        Tries to pull a title (first non-empty line) and author names
        (lines between title and abstract).
        """
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        metadata: dict[str, Any] = {"source_file": str(file_path)}

        if not lines:
            return metadata

        # Title — usually the first meaningful line.
        metadata["title"] = lines[0]

        # Authors — heuristic: lines between title and "abstract" header,
        # which often contain comma/semicolon-separated names.
        authors: list[str] = []
        for line in lines[1:15]:
            if re.match(r"(?:abstract|introduction)\b", line, re.IGNORECASE):
                break
            # Likely an author line if it contains commas and no numbers
            if re.search(r"[A-Z][a-z]+", line) and not re.search(r"\d{4,}", line):
                # Split on comma, semicolon, or " and "
                parts = re.split(r"[;,]|\band\b", line)
                for part in parts:
                    name = part.strip()
                    if 2 < len(name) < 80 and not re.match(r"^(?:university|department|institute|school)\b", name, re.IGNORECASE):
                        authors.append(name)

        if authors:
            metadata["authors"] = authors

        return metadata

    # ------------------------------------------------------------------
    # Raw text ingestion
    # ------------------------------------------------------------------

    async def ingest_from_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestedPaper:
        """Ingest raw text with optional caller-supplied metadata.

        Args:
            text: The full document text.
            metadata: Arbitrary metadata dict.

        Returns:
            An :class:`IngestedPaper`.
        """
        metadata = metadata or {}

        # Normalise
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        sections = self._detect_sections(text)

        logger.info(
            "ingest.text_complete",
            text_len=len(text),
            sections_found=list(sections.keys()),
        )

        return IngestedPaper(
            text=text,
            metadata=metadata,
            sections=sections,
            source="text",
        )

    # ------------------------------------------------------------------
    # Section detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_sections(text: str) -> dict[str, str]:
        """Detect and extract academic paper sections from *text*.

        Each section spans from its heading to the beginning of the next
        detected heading (or end of document).

        Returns:
            Ordered dict of ``section_name -> section_body``.
        """
        # Find all heading positions.
        matches: list[tuple[int, int, str]] = []
        for name, pattern in _SECTION_PATTERNS:
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), name))

        if not matches:
            return {}

        # Sort by position.
        matches.sort(key=lambda x: x[0])

        sections: dict[str, str] = {}
        for i, (start, heading_end, name) in enumerate(matches):
            if i + 1 < len(matches):
                section_end = matches[i + 1][0]
            else:
                section_end = len(text)

            body = text[heading_end:section_end].strip()
            if body:
                # If we have duplicate section names, append a suffix.
                key = name
                suffix = 2
                while key in sections:
                    key = f"{name}_{suffix}"
                    suffix += 1
                sections[key] = body

        return sections
