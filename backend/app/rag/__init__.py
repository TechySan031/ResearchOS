"""RAG (Retrieval-Augmented Generation) pipeline for ResearchOS.

This package provides:
- Paper ingestion from arXiv, PDFs, and raw text
- Semantic chunking with section awareness
- Embedding generation via BGE-large
- Pinecone-backed vector store operations
- Semantic retrieval with reranking
- Citation grounding and verification
"""

from app.rag.chunking import ChunkingStrategy, TextChunk, TextChunker
from app.rag.embeddings import EmbeddingGenerator
from app.rag.grounding import CitationGrounder, GroundingLevel, GroundingResult
from app.rag.ingestion import IngestedPaper, PaperIngestor
from app.rag.retriever import RetrievalResult, SemanticRetriever
from app.rag.vectorstore import SearchResult, VectorStore
from app.rag.verification import RetrievalVerifier, VerificationReport

__all__ = [
    "ChunkingStrategy",
    "CitationGrounder",
    "EmbeddingGenerator",
    "GroundingLevel",
    "GroundingResult",
    "IngestedPaper",
    "PaperIngestor",
    "RetrievalResult",
    "RetrievalVerifier",
    "SearchResult",
    "SemanticRetriever",
    "TextChunk",
    "TextChunker",
    "VerificationReport",
    "VectorStore",
]
