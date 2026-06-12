"""LangGraph workflow builder for ResearchOS.

Constructs the full multi-agent research workflow graph with all nodes,
conditional edges (driven by the deterministic supervisor), and
checkpointing.

All 11 agent nodes are now real implementations backed by LLM calls
(Mistral / Kimi) — no more placeholders.

Usage::

    graph = build_research_graph()
    final_state = await run_workflow("quantum computing survey", "proj-123")
"""

from __future__ import annotations

import datetime as _dt
from typing import Any
import traceback
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, END
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import ResearchState
from app.agents.supervisor import route
from app.agents.nodes import (
    research_retrieval_node,
    literature_review_node,
    citation_verification_node,
    gap_analysis_node,
    methodology_suggestion_node,
    draft_writing_node,
    hallucination_detection_node,
    formatting_node,
    journal_recommendation_node,
    reviewer_simulation_node,
    submission_preparation_node,
)
from app.core.events import EventBus, AgentEvent
from app.utils.logging import get_logger

logger = get_logger(__name__)
import time

# ── Build the compiled graph ────────────────────────────────────────────


def build_research_graph() -> Any:
    """Construct and compile the LangGraph research workflow.

    Returns:
        A compiled LangGraph ``CompiledGraph`` with ``MemorySaver``
        checkpointing enabled.
    """
    workflow = StateGraph(ResearchState)

    # ── Register all agent nodes ────────────────────────────────────
    workflow.add_node("research_retrieval", research_retrieval_node)
    workflow.add_node("literature_review", literature_review_node)
    workflow.add_node("citation_verification", citation_verification_node)
    workflow.add_node("gap_analysis", gap_analysis_node)
    workflow.add_node("methodology_suggestion", methodology_suggestion_node)
    workflow.add_node("draft_writing", draft_writing_node)
    workflow.add_node("hallucination_detection", hallucination_detection_node)
    workflow.add_node("formatting", formatting_node)
    workflow.add_node("journal_recommendation", journal_recommendation_node)
    workflow.add_node("reviewer_simulation", reviewer_simulation_node)
    workflow.add_node("submission_preparation", submission_preparation_node)

    # ── Virtual supervisor node (conditional routing) ───────────────
    workflow.add_node("supervisor", _supervisor_node)

    # ── Entry point ────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    # ── Conditional edges from supervisor ──────────────────────────
    workflow.add_conditional_edges(
        "supervisor",
        route,
        {
            "research_retrieval": "research_retrieval",
            "literature_review": "literature_review",
            "citation_verification": "citation_verification",
            "gap_analysis": "gap_analysis",
            "methodology_suggestion": "methodology_suggestion",
            "draft_writing": "draft_writing",
            "hallucination_detection": "hallucination_detection",
            "formatting": "formatting",
            "journal_recommendation": "journal_recommendation",
            "reviewer_simulation": "reviewer_simulation",
            "submission_preparation": "submission_preparation",
            "END": END,
        },
    )

    # ── Every worker node feeds back into the supervisor ───────────
    _worker_nodes = [
        "research_retrieval",
        "literature_review",
        "citation_verification",
        "gap_analysis",
        "methodology_suggestion",
        "draft_writing",
        "hallucination_detection",
        "formatting",
        "journal_recommendation",
        "reviewer_simulation",
        "submission_preparation",
    ]
    for node_name in _worker_nodes:
        workflow.add_edge(node_name, "supervisor")

    # ── Compile with checkpointer ──────────────────────────────────
    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)

    logger.info("graph.compiled", node_count=len(_worker_nodes) + 1)
    return compiled


async def _supervisor_node(state: ResearchState) -> dict[str, Any]:
    """Thin pass-through node used as the routing hub.

    The actual routing logic is in ``supervisor.route`` and is wired via
    ``add_conditional_edges``.  This node just logs the transition.
    """
    logger.debug(
        "supervisor.enter",
        current_agent=state.get("current_agent"),
        status=state.get("status"),
        project_id=state.get("project_id"),
    )
    return {"current_agent": "supervisor"}


# ── Convenience runner ──────────────────────────────────────────────────


async def run_workflow(
    topic: str,
    project_id: str,
    *,
    user_preferences: dict[str, Any] | None = None,
    max_revisions: int = 3,
    format_style: str = "ieee",
) -> ResearchState:
    """Run the full research workflow end-to-end.

    This is a high-level convenience function intended for services and
    CLI scripts.  It builds the graph, prepares the initial state, and
    invokes the compiled graph asynchronously.

    Args:
        topic: The user's research topic / question.
        project_id: UUID of the owning project.
        user_preferences: Optional dict of user preferences.
        max_revisions: Maximum number of revision loops (default 3).
        format_style: Target formatting style (default ``"ieee"``).

    Returns:
        The final ``ResearchState`` after the workflow completes.
    """
    workflow_start_ns = time.monotonic_ns()
    logger.info(
        "workflow.start",
        topic=topic,
        project_id=project_id,
        max_revisions=max_revisions,
    )

    graph = build_research_graph()

    initial_state: dict[str, Any] = {
        "topic": topic,
        "project_id": project_id,
        "user_preferences": user_preferences or {},
        "retrieved_papers": [],
        "paper_embeddings_stored": False,
        "literature_review": "",
        "key_themes": [],
        "citations": [],
        "citation_verification_results": [],
        "research_gaps": [],
        "suggested_methodologies": [],
        "selected_methodology": None,
        "paper_outline": {},
        "paper_sections": {},
        "hallucination_report": {},
        "formatted_paper": "",
        "format_style": format_style,
        "journal_recommendations": [],
        "reviewer_feedback": [],
        "submission_package": {},
        "current_agent": "",
        "agent_history": [],
        "errors": [],
        "status": "initialized",
        "messages": [],
        "revision_count": 0,
        "max_revisions": max_revisions,
    }

    config = {"configurable": {"thread_id": project_id}}

    try:
        # Publish workflow start event
        try:
            bus = EventBus()
            await bus.publish(
                AgentEvent(
                    agent_name="supervisor",
                    event_type="workflow_started",
                    project_id=project_id,
                    data={"topic": topic, "format_style": format_style},
                )
            )
        except Exception:
            pass

        final_state = await graph.ainvoke(initial_state, config=config)
        workflow_duration_ms = (
            time.monotonic_ns() - workflow_start_ns
        ) / 1_000_000
        
        # Publish workflow completion event
        try:
            bus = EventBus()

    
            await bus.publish(
                AgentEvent(
                     agent_name="supervisor",
                     event_type="workflow_completed",
                     project_id=project_id,
                     data={
                           "status": final_state.get("status"),
                           "agents_executed": len(
                                      final_state.get("agent_history", [])
                            ),
                            "workflow_duration_ms": round(
                                      workflow_duration_ms,
                                           2,
                            ),
                        },
                    )
                )

        except Exception:
             pass

        logger.info(
            "workflow.complete",
            project_id=project_id,
            status=final_state.get("status"),
            agents_executed=len(final_state.get("agent_history", [])),
        )
        return final_state  # type: ignore[return-value]

    except Exception as exc:
        logger.error(
            "workflow.failed",
            project_id=project_id,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
