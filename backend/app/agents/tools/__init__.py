"""LangChain tool wrappers for external research APIs and RAG pipeline."""

from app.agents.tools.arxiv_tool import search_arxiv
from app.agents.tools.semantic_scholar_tool import (
    search_semantic_scholar,
    get_paper_details,
)
from app.agents.tools.crossref_tool import verify_doi, search_crossref
from app.agents.tools.vector_search_tool import semantic_search

__all__ = [
    "search_arxiv",
    "search_semantic_scholar",
    "get_paper_details",
    "verify_doi",
    "search_crossref",
    "semantic_search",
]
