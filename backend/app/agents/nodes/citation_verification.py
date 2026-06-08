"""Citation verification agent node — verifies DOIs and reference accuracy."""

from __future__ import annotations
import datetime as _dt
from typing import Any
from app.agents.state import ResearchState
from app.agents.nodes.base import publish_event, make_history_entry, make_error_entry, _papers_context
from app.agents.prompts.citation_verification import CITATION_VERIFICATION_PROMPT
from app.integrations.llm_client import LLMClient
from app.integrations.crossref_client import CrossRefClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def citation_verification_node(state: ResearchState) -> dict[str, Any]:
    """LangGraph node: verify citations from the literature review.

    Cross-references cited papers with CrossRef DOI data and uses Mistral
    to assess citation accuracy and contextual relevance.
    """
    project_id = state.get("project_id", "")
    papers = state.get("retrieved_papers", [])
    review = state.get("literature_review", "")
    start = _dt.datetime.now(_dt.timezone.utc)

    logger.info("citation_verification.start", project_id=project_id)
    await publish_event("citation_verification", "started", project_id)

    # Step 1: Verify DOIs via CrossRef
    crossref = CrossRefClient()
    doi_results = []
    for paper in papers:
        doi = paper.get("doi", "")
        if doi:
            try:
                is_valid = await crossref.verify_doi(doi)
                doi_results.append({"doi": doi, "title": paper.get("title", ""), "valid": is_valid})
            except Exception:
                doi_results.append({"doi": doi, "title": paper.get("title", ""), "valid": False})

    # Step 2: LLM-based contextual verification
    context = _papers_context(papers)
    user_prompt = (
        f"## Literature Review\n{review[:6000]}\n\n"
        f"## Papers to Verify\n{context}\n\n"
        f"## DOI Verification Results\n{_format_doi_results(doi_results)}"
    )

    try:
        llm = LLMClient()
        result = await llm.generate_json(
            provider="mistral",
            system_prompt=CITATION_VERIFICATION_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error("citation_verification.llm_error", error=str(e))
        return {
            "current_agent": "citation_verification",
            "agent_history": [make_history_entry("citation_verification", "failed")],
            "errors": [make_error_entry("citation_verification", str(e))],
            "citation_verification_results": doi_results,
        }

    verification_results = result.get("verification_results", doi_results)
    summary = result.get("summary", {})
    elapsed = (_dt.datetime.now(_dt.timezone.utc) - start).total_seconds()

    # Build citation objects
    citations = []
    for i, paper in enumerate(papers):
        citations.append({
            "citation_key": f"REF_{i+1}",
            "paper_title": paper.get("title", ""),
            "doi": paper.get("doi", ""),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "source": paper.get("source", ""),
        })

    await publish_event("citation_verification", "completed", project_id, {
        "verified": summary.get("verified", 0), "total": summary.get("total", len(papers)), "elapsed": elapsed,
    })
    logger.info("citation_verification.complete", elapsed=elapsed)

    return {
        "citations": citations,
        "citation_verification_results": verification_results,
        "current_agent": "citation_verification",
        "agent_history": [make_history_entry("citation_verification", elapsed=elapsed, summary=summary)],
        "status": "citations_verified",
    }


def _format_doi_results(results: list[dict]) -> str:
    lines = []
    for r in results:
        status = "✓ Valid" if r.get("valid") else "✗ Invalid/Missing"
        lines.append(f"- {r.get('title', 'Unknown')}: DOI {r.get('doi', 'N/A')} — {status}")
    return "\n".join(lines) if lines else "No DOIs to verify."
