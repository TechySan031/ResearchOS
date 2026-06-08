"""External service integrations for ResearchOS.

This package provides async clients for:
- arXiv paper search and retrieval
- Semantic Scholar academic graph API
- CrossRef metadata verification
- Redis caching and pub/sub
- Pinecone vector database
- Mistral and Kimi LLM providers
"""

from app.integrations.arxiv_client import ArxivClient, ArxivPaper
from app.integrations.crossref_client import CrossRefClient, CrossRefWork
from app.integrations.llm_client import LLMClient
from app.integrations.pinecone_client import PineconeManager, QueryResult
from app.integrations.redis_client import RedisManager
from app.integrations.semantic_scholar_client import SemanticScholarClient, S2Paper

__all__ = [
    "ArxivClient",
    "ArxivPaper",
    "CrossRefClient",
    "CrossRefWork",
    "LLMClient",
    "PineconeManager",
    "QueryResult",
    "RedisManager",
    "SemanticScholarClient",
    "S2Paper",
]
