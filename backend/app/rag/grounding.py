"""
ResearchOS — Citation Grounding

Verifies that generated claims are grounded in source documents.
Every claim with a [REF_n] marker is checked against the vector
store for semantic similarity with source chunks.

Grounding levels:
  - STRONG (>= 0.80): Claim closely matches source
  - MODERATE (0.65-0.80): Reasonable support found
  - WEAK (0.50-0.65): Marginal support
  - UNGROUNDED (< 0.50): No supporting evidence found
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from app.rag.embeddings import EmbeddingGenerator
from app.rag.vectorstore import VectorStore
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GroundingLevel(str, Enum):
    """Classification of how well a claim is supported by sources."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNGROUNDED = "ungrounded"


@dataclass
class GroundingResult:
    """Result of grounding verification for a single claim."""
    claim_text: str
    source_text: str
    source_paper_id: str
    source_doi: str
    similarity_score: float
    grounding_level: GroundingLevel
    citation_key: str = ""
    source_title: str = ""
    source_section: str = ""


@dataclass
class SectionGroundingReport:
    """Aggregated grounding report for a document section."""
    section_name: str
    total_claims: int
    strong_count: int = 0
    moderate_count: int = 0
    weak_count: int = 0
    ungrounded_count: int = 0
    avg_grounding_score: float = 0.0
    results: list[GroundingResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def grounding_ratio(self) -> float:
        """Fraction of claims that are at least moderately grounded."""
        if self.total_claims == 0:
            return 1.0
        return (self.strong_count + self.moderate_count) / self.total_claims


# Regex patterns for extracting citation markers
CITATION_PATTERN = re.compile(r'\[REF_(\d+)\]')
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


class CitationGrounder:
    """
    Verifies that generated text claims are grounded in source documents.

    For each claim sentence containing a citation marker [REF_n],
    retrieves the most relevant source chunk from Pinecone and
    computes semantic similarity.
    """

    # Grounding thresholds
    STRONG_THRESHOLD = 0.80
    MODERATE_THRESHOLD = 0.65
    WEAK_THRESHOLD = 0.50

    def __init__(
        self,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self._embedder = embedding_generator or EmbeddingGenerator()
        self._vectorstore = vector_store or VectorStore()

    def _classify_score(self, score: float) -> GroundingLevel:
        """Classify a similarity score into a grounding level."""
        if score >= self.STRONG_THRESHOLD:
            return GroundingLevel.STRONG
        elif score >= self.MODERATE_THRESHOLD:
            return GroundingLevel.MODERATE
        elif score >= self.WEAK_THRESHOLD:
            return GroundingLevel.WEAK
        else:
            return GroundingLevel.UNGROUNDED

    def _extract_cited_sentences(self, text: str) -> list[tuple[str, str]]:
        """
        Extract sentences containing citation markers.

        Returns list of (clean_sentence, citation_key) tuples.
        """
        sentences = SENTENCE_PATTERN.split(text)
        cited = []

        for sentence in sentences:
            sentence = sentence.strip()
            match = CITATION_PATTERN.search(sentence)
            if match:
                citation_key = f"REF_{match.group(1)}"
                # Remove the citation marker for embedding
                clean = CITATION_PATTERN.sub('', sentence).strip()
                if clean:
                    cited.append((clean, citation_key))

        return cited

    async def ground_claim(
        self,
        claim_text: str,
        project_id: str,
        citation_key: str = "",
    ) -> GroundingResult:
        """
        Verify a single claim against the vector store.

        Args:
            claim_text: The claim sentence to verify.
            project_id: Project ID for vector store filtering.
            citation_key: Optional citation key (e.g., "REF_1").

        Returns:
            GroundingResult with similarity score and level.
        """
        logger.debug(
            "grounding_claim",
            claim_preview=claim_text[:80],
            project_id=project_id,
        )

        # Generate embedding for the claim
        claim_embedding = await self._embedder.generate_single(claim_text)

        # Search for the most similar source chunk
        search_results = await self._vectorstore.search(
            query_embedding=claim_embedding,
            project_id=project_id,
            top_k=3,  # Get top 3 and pick best
        )

        if not search_results:
            logger.warning(
                "no_sources_found_for_claim",
                claim_preview=claim_text[:80],
            )
            return GroundingResult(
                claim_text=claim_text,
                source_text="",
                source_paper_id="",
                source_doi="",
                similarity_score=0.0,
                grounding_level=GroundingLevel.UNGROUNDED,
                citation_key=citation_key,
            )

        # Use the best match
        best = search_results[0]

        # Compute cosine similarity between claim and source embeddings
        # (The search score from Pinecone is already cosine similarity)
        similarity = best.score

        grounding_level = self._classify_score(similarity)

        return GroundingResult(
            claim_text=claim_text,
            source_text=best.chunk_text,
            source_paper_id=best.paper_id,
            source_doi=best.doi,
            similarity_score=round(similarity, 4),
            grounding_level=grounding_level,
            citation_key=citation_key,
            source_title=best.title,
            source_section=best.section,
        )

    async def ground_section(
        self,
        section_text: str,
        section_name: str,
        project_id: str,
    ) -> SectionGroundingReport:
        """
        Verify all cited claims in a document section.

        Args:
            section_text: Full text of the section with [REF_n] markers.
            section_name: Name of the section (e.g., "introduction").
            project_id: Project ID for vector store filtering.

        Returns:
            SectionGroundingReport with per-claim results and aggregates.
        """
        logger.info(
            "grounding_section",
            section=section_name,
            text_length=len(section_text),
        )

        # Extract sentences with citations
        cited_sentences = self._extract_cited_sentences(section_text)

        if not cited_sentences:
            logger.info(
                "no_citations_in_section",
                section=section_name,
            )
            return SectionGroundingReport(
                section_name=section_name,
                total_claims=0,
            )

        # Ground each claim
        results = []
        scores = []

        for claim_text, citation_key in cited_sentences:
            result = await self.ground_claim(
                claim_text=claim_text,
                project_id=project_id,
                citation_key=citation_key,
            )
            results.append(result)
            scores.append(result.similarity_score)

        # Build report
        report = SectionGroundingReport(
            section_name=section_name,
            total_claims=len(results),
            strong_count=sum(1 for r in results if r.grounding_level == GroundingLevel.STRONG),
            moderate_count=sum(1 for r in results if r.grounding_level == GroundingLevel.MODERATE),
            weak_count=sum(1 for r in results if r.grounding_level == GroundingLevel.WEAK),
            ungrounded_count=sum(1 for r in results if r.grounding_level == GroundingLevel.UNGROUNDED),
            avg_grounding_score=round(float(np.mean(scores)), 4) if scores else 0.0,
            results=results,
        )

        # Add warnings
        if report.ungrounded_count > 0:
            report.warnings.append(
                f"{report.ungrounded_count} claim(s) have no supporting evidence "
                f"and may be hallucinated."
            )
        if report.grounding_ratio < 0.7:
            report.warnings.append(
                f"Section grounding ratio is {report.grounding_ratio:.0%}, "
                f"below the 70% threshold. Consider revising."
            )

        logger.info(
            "section_grounding_complete",
            section=section_name,
            total_claims=report.total_claims,
            strong=report.strong_count,
            moderate=report.moderate_count,
            weak=report.weak_count,
            ungrounded=report.ungrounded_count,
            avg_score=report.avg_grounding_score,
        )

        return report

    async def ground_document(
        self,
        sections: dict[str, str],
        project_id: str,
    ) -> dict[str, SectionGroundingReport]:
        """
        Verify all citations across all sections of a document.

        Args:
            sections: Dict of section_name -> section_text.
            project_id: Project ID.

        Returns:
            Dict of section_name -> SectionGroundingReport.
        """
        reports = {}
        for section_name, section_text in sections.items():
            report = await self.ground_section(
                section_text=section_text,
                section_name=section_name,
                project_id=project_id,
            )
            reports[section_name] = report

        total_claims = sum(r.total_claims for r in reports.values())
        total_ungrounded = sum(r.ungrounded_count for r in reports.values())

        logger.info(
            "document_grounding_complete",
            total_sections=len(reports),
            total_claims=total_claims,
            total_ungrounded=total_ungrounded,
        )

        return reports
