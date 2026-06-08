"""ResearchOS agent node implementations.

Each module exports a single async node function compatible with
LangGraph's StateGraph interface.
"""

from app.agents.nodes.research_retrieval import research_retrieval_node
from app.agents.nodes.literature_review import literature_review_node
from app.agents.nodes.citation_verification import citation_verification_node
from app.agents.nodes.gap_analysis import gap_analysis_node
from app.agents.nodes.methodology_suggestion import methodology_suggestion_node
from app.agents.nodes.draft_writing import draft_writing_node
from app.agents.nodes.hallucination_detection import hallucination_detection_node
from app.agents.nodes.formatting import formatting_node
from app.agents.nodes.journal_recommendation import journal_recommendation_node
from app.agents.nodes.reviewer_simulation import reviewer_simulation_node
from app.agents.nodes.submission_preparation import submission_preparation_node

__all__ = [
    "research_retrieval_node",
    "literature_review_node",
    "citation_verification_node",
    "gap_analysis_node",
    "methodology_suggestion_node",
    "draft_writing_node",
    "hallucination_detection_node",
    "formatting_node",
    "journal_recommendation_node",
    "reviewer_simulation_node",
    "submission_preparation_node",
]
