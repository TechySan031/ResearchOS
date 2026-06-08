"""
ResearchOS — Test Fixtures

Shared pytest fixtures for unit and integration tests.
"""

import asyncio
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import create_app
from app.models.database import Base
from app.dependencies import get_db


# ---- Event Loop ----

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- Database ----

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session."""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---- FastAPI Test Client ----

@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx AsyncClient connected to the test app.

    Overrides the database dependency to use the test session.
    """
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ---- Sample Data ----

@pytest.fixture
def sample_project_data():
    """Sample project creation data."""
    return {
        "title": "Test Research Project",
        "topic": "Transformer architectures for protein structure prediction",
        "settings": {
            "format_style": "ieee",
            "max_papers": 20,
        },
    }


@pytest.fixture
def sample_paper_data():
    """Sample paper data as returned from APIs."""
    return {
        "external_id": "2401.12345",
        "source": "arxiv",
        "doi": "10.1234/test.2024.001",
        "title": "Attention Mechanisms in Protein Folding",
        "authors": ["Alice Smith", "Bob Jones"],
        "abstract": (
            "We present a novel attention mechanism for predicting "
            "protein tertiary structure from amino acid sequences."
        ),
        "year": 2024,
        "venue": "NeurIPS 2024",
        "url": "https://arxiv.org/abs/2401.12345",
        "pdf_url": "https://arxiv.org/pdf/2401.12345",
        "citation_count": 42,
    }


@pytest.fixture
def sample_research_request():
    """Sample research start request."""
    return {
        "topic": "Transformer architectures for protein structure prediction",
        "max_papers": 15,
        "sources": ["arxiv", "semantic_scholar"],
        "format_style": "ieee",
    }


@pytest.fixture
def sample_chunk_text():
    """Sample text chunk for embedding/retrieval tests."""
    return (
        "Recent advances in transformer-based architectures have shown "
        "remarkable success in protein structure prediction tasks. "
        "AlphaFold2 demonstrated that attention mechanisms can capture "
        "long-range dependencies in amino acid sequences, achieving "
        "near-experimental accuracy in structure determination."
    )


# ---- Mocks ----

@pytest.fixture
def mock_redis():
    """Mock Redis manager for tests that don't need real Redis."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.incr_with_ttl = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def mock_embedding_generator():
    """Mock embedding generator that returns fixed-dimension vectors."""
    mock = AsyncMock()
    # Return a deterministic 1024-dim vector
    mock.generate_single = AsyncMock(return_value=[0.1] * 1024)
    mock.generate = AsyncMock(return_value=[[0.1] * 1024])
    return mock


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone manager."""
    mock = AsyncMock()
    mock.query = AsyncMock(return_value=[])
    mock.upsert_vectors = AsyncMock(return_value=None)
    mock.delete_by_filter = AsyncMock(return_value=None)
    mock.get_index_stats = AsyncMock(return_value={"total_count": 0})
    return mock
