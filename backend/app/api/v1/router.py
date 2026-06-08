"""
ResearchOS — Aggregated V1 API Router

Combines all v1 endpoint routers under a single prefix with tags
for OpenAPI documentation grouping.
"""

from fastapi import APIRouter

from app.api.v1.projects import router as projects_router
from app.api.v1.papers import router as papers_router
from app.api.v1.research import router as research_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.documents import router as documents_router
from app.api.v1.citations import router as citations_router
from app.api.v1.agents import router as agents_router
from app.api.v1.streaming import router as streaming_router


v1_router = APIRouter()

# ---- Project Management ----
v1_router.include_router(
    projects_router,
    prefix="/projects",
    tags=["Projects"],
)

# ---- Paper Retrieval & Management ----
v1_router.include_router(
    papers_router,
    prefix="/projects/{project_id}/papers",
    tags=["Papers"],
)

# ---- Research Workflow ----
v1_router.include_router(
    research_router,
    prefix="/projects/{project_id}/research",
    tags=["Research Workflow"],
)

# ---- Documents ----
v1_router.include_router(
    documents_router,
    prefix="/projects/{project_id}/document",
    tags=["Documents"],
)

# ---- Citations ----
v1_router.include_router(
    citations_router,
    prefix="/projects/{project_id}/citations",
    tags=["Citations"],
)

# ---- Agents ----
v1_router.include_router(
    agents_router,
    prefix="/projects/{project_id}/agents",
    tags=["Agents"],
)

# ---- WebSocket ----
v1_router.include_router(
    websocket_router,
    tags=["WebSocket"],
)

# ---- SSE Streaming ----
v1_router.include_router(
    streaming_router,
    prefix="/projects/{project_id}",
    tags=["Streaming"],
)
