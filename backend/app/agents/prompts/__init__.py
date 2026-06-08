"""ResearchOS agent prompt definitions.

Each module exports a single prompt string constant used as the
system prompt for the corresponding LLM-powered agent node.
"""

from app.agents.prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT
from app.agents.prompts.retrieval import RETRIEVAL_SYSTEM_PROMPT
from app.agents.prompts.literature_review import LITERATURE_REVIEW_PROMPT
from app.agents.prompts.citation_verification import CITATION_VERIFICATION_PROMPT
from app.agents.prompts.gap_analysis import GAP_ANALYSIS_PROMPT
from app.agents.prompts.methodology import METHODOLOGY_PROMPT
from app.agents.prompts.draft_writing import DRAFT_WRITING_PROMPT
from app.agents.prompts.hallucination import HALLUCINATION_PROMPT
from app.agents.prompts.formatting import FORMATTING_PROMPT
from app.agents.prompts.journal import JOURNAL_PROMPT
from app.agents.prompts.reviewer import REVIEWER_PROMPT
from app.agents.prompts.submission import SUBMISSION_PROMPT

# Convenience aliases
SUPERVISOR_PROMPT = SUPERVISOR_SYSTEM_PROMPT
RETRIEVAL_PROMPT = RETRIEVAL_SYSTEM_PROMPT

__all__ = [
    "SUPERVISOR_SYSTEM_PROMPT",
    "SUPERVISOR_PROMPT",
    "RETRIEVAL_SYSTEM_PROMPT",
    "RETRIEVAL_PROMPT",
    "LITERATURE_REVIEW_PROMPT",
    "CITATION_VERIFICATION_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "METHODOLOGY_PROMPT",
    "DRAFT_WRITING_PROMPT",
    "HALLUCINATION_PROMPT",
    "FORMATTING_PROMPT",
    "JOURNAL_PROMPT",
    "REVIEWER_PROMPT",
    "SUBMISSION_PROMPT",
]
