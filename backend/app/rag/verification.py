"""
ResearchOS — Retrieval Verification

Quality checks for retrieval results: relevance scoring,
source diversity analysis, recency assessment, and warnings
for potential issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VerificationReport:
    """Aggregated quality report for a set of retrieval results."""
    avg_relevance_score: float
    diversity_score: float
    recency_score: float
    total_sources: int
    total_results: int
    unique_papers: int
    unique_sections: int
    year_range: tuple[int, int] = (0, 0)
    warnings: list[str] = field(default_factory=list)
    quality_grade: str = "unknown"  # A, B, C, D, F

    def is_acceptable(self) -> bool:
        """Check if retrieval quality meets minimum thresholds."""
        return (
            self.avg_relevance_score >= 0.5
            and self.diversity_score >= 0.3
            and self.total_results >= 3
        )


class RetrievalVerifier:
    """
    Verifies the quality of retrieval results before they're used
    by agents for generation.

    Checks:
    1. Relevance — are the retrieved chunks related to the query?
    2. Diversity — are results from multiple distinct sources?
    3. Recency — are recent papers represented?
    """

    # Thresholds
    MIN_RELEVANCE_SCORE = 0.5
    MIN_DIVERSITY_RATIO = 0.3
    RECENCY_YEARS = 5  # Papers within last N years are "recent"

    async def verify_retrieval_quality(
        self,
        query: str,
        results: list,
        current_year: Optional[int] = None,
    ) -> VerificationReport:
        """
        Run quality checks on retrieval results.

        Args:
            query: The original search query.
            results: List of retrieval results (must have score, paper_id,
                     title, section, and metadata attributes or dict keys).
            current_year: Override for current year (for testing).

        Returns:
            VerificationReport with scores, warnings, and quality grade.
        """
        if not results:
            return VerificationReport(
                avg_relevance_score=0.0,
                diversity_score=0.0,
                recency_score=0.0,
                total_sources=0,
                total_results=0,
                unique_papers=0,
                unique_sections=0,
                warnings=["No retrieval results found."],
                quality_grade="F",
            )

        now_year = current_year or datetime.now(timezone.utc).year

        # ---- Extract data from results ----
        scores = []
        paper_ids = set()
        sections = set()
        years = []

        for r in results:
            # Support both dataclass and dict access
            if isinstance(r, dict):
                scores.append(r.get("score", 0.0))
                paper_ids.add(r.get("paper_id", ""))
                sections.add(r.get("section", ""))
                year = r.get("metadata", {}).get("year") or r.get("year")
            else:
                scores.append(getattr(r, "score", 0.0))
                paper_ids.add(getattr(r, "paper_id", ""))
                sections.add(getattr(r, "section", ""))
                meta = getattr(r, "metadata", {})
                year = meta.get("year") if isinstance(meta, dict) else None

            if year and isinstance(year, (int, float)):
                years.append(int(year))

        # ---- Relevance Score ----
        avg_relevance = sum(scores) / len(scores) if scores else 0.0

        # ---- Diversity Score ----
        # Ratio of unique papers to total results
        unique_paper_count = len(paper_ids - {""})
        diversity = (
            unique_paper_count / len(results)
            if results
            else 0.0
        )

        # ---- Recency Score ----
        if years:
            recent_count = sum(1 for y in years if (now_year - y) <= self.RECENCY_YEARS)
            recency = recent_count / len(years)
            year_range = (min(years), max(years))
        else:
            recency = 0.0
            year_range = (0, 0)

        # ---- Warnings ----
        warnings = []

        if avg_relevance < self.MIN_RELEVANCE_SCORE:
            warnings.append(
                f"Average relevance score ({avg_relevance:.2f}) is below "
                f"threshold ({self.MIN_RELEVANCE_SCORE}). Results may not "
                f"be sufficiently related to the query."
            )

        if diversity < self.MIN_DIVERSITY_RATIO:
            warnings.append(
                f"Source diversity ({diversity:.2f}) is low. Results are "
                f"concentrated in {unique_paper_count} paper(s). Consider "
                f"broadening the search."
            )

        if recency < 0.3 and years:
            warnings.append(
                f"Only {recency:.0%} of results are from the last "
                f"{self.RECENCY_YEARS} years. The field may have evolved."
            )

        if len(results) < 3:
            warnings.append(
                f"Only {len(results)} result(s) retrieved. Consider "
                f"relaxing search constraints for broader coverage."
            )

        low_score_count = sum(1 for s in scores if s < 0.5)
        if low_score_count > len(scores) / 2:
            warnings.append(
                f"{low_score_count}/{len(scores)} results have similarity "
                f"below 0.5, indicating weak relevance."
            )

        # ---- Quality Grade ----
        composite = (
            avg_relevance * 0.5
            + diversity * 0.3
            + recency * 0.2
        )

        if composite >= 0.8:
            grade = "A"
        elif composite >= 0.65:
            grade = "B"
        elif composite >= 0.5:
            grade = "C"
        elif composite >= 0.35:
            grade = "D"
        else:
            grade = "F"

        report = VerificationReport(
            avg_relevance_score=round(avg_relevance, 4),
            diversity_score=round(diversity, 4),
            recency_score=round(recency, 4),
            total_sources=unique_paper_count,
            total_results=len(results),
            unique_papers=unique_paper_count,
            unique_sections=len(sections - {""}),
            year_range=year_range,
            warnings=warnings,
            quality_grade=grade,
        )

        logger.info(
            "retrieval_verification_complete",
            query_preview=query[:80],
            grade=grade,
            avg_relevance=report.avg_relevance_score,
            diversity=report.diversity_score,
            recency=report.recency_score,
            total_results=report.total_results,
            warnings_count=len(warnings),
        )

        return report
