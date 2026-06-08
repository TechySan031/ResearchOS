<div align="center">

# 🔬 ResearchOS

### AI Research Operating System

*A production-grade, multi-agent research workflow automation platform*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)

</div>

---

## Overview

ResearchOS is an **AI-powered research operating system** that automates the complete lifecycle of academic paper creation — from literature discovery to publication-ready output.

Unlike simple chatbot wrappers, ResearchOS orchestrates **12 specialized AI agents** through a deterministic supervisor architecture, backed by **real RAG pipelines** with citation grounding, hallucination detection, and verification loops.

### What It Does

1. 📚 **Retrieves** relevant papers from arXiv, Semantic Scholar, and CrossRef
2. 🧠 **Builds** a semantic knowledge base using embeddings + Pinecone vector DB
3. 📝 **Performs** automated literature review with source attribution
4. 🔍 **Identifies** research gaps in the existing literature
5. 🔬 **Suggests** methodologies based on identified gaps
6. ✍️ **Generates** structured paper drafts with inline citations
7. ✅ **Validates** every citation and reference for accuracy
8. 🛡️ **Detects** hallucination risks with grounding verification
9. 📄 **Formats** papers in IEEE / ACM / Springer style
10. 📮 **Assists** publication workflows with journal recommendations
11. 🎯 **Simulates** peer review with AI reviewer agents
12. 📦 **Generates** export-ready submission packages

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                        │
│  Dashboard │ Workspace │ Editor │ Agent Timeline │ Export   │
└──────────────────────┬──────────────────────────────────────┘
                       │ WebSocket + REST
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                           │
│  Routers │ Middleware │ Services │ Background Workers        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              LangGraph Multi-Agent Orchestration             │
│  Supervisor → Retrieval → Review → Gaps → Draft → Verify   │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
    ┌──────▼──────┐                 ┌──────▼──────┐
    │  RAG Engine  │                │  LLM Layer   │
    │  Pinecone    │                │  Mistral     │
    │  BGE-large   │                │  Kimi        │
    └─────────────┘                 └─────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, Tailwind CSS, shadcn/ui, Framer Motion |
| Backend | Python, FastAPI, SQLAlchemy 2.0 |
| AI Orchestration | LangGraph (supervisor pattern) |
| Vector Database | Pinecone (serverless) |
| Embeddings | BAAI/bge-large-en-v1.5 |
| LLMs | Mistral (structured gen), Kimi (long context) |
| Caching | Redis |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Research APIs | arXiv, Semantic Scholar, CrossRef |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional for dev — falls back gracefully)
- API keys for Mistral, Kimi, Pinecone, Semantic Scholar

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ResearchOS.git
cd ResearchOS

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Start development servers
cd ..
make dev
```

### Running Services

```bash
# Backend only (port 8000)
make backend

# Frontend only (port 3000)
make frontend

# Start Redis (optional)
docker-compose up -d

# Run tests
make test
```

---

## Project Structure

```
ResearchOS/
├── backend/          # FastAPI + LangGraph backend
│   ├── app/
│   │   ├── agents/   # Multi-agent system (LangGraph)
│   │   ├── api/      # REST + WebSocket endpoints
│   │   ├── core/     # Exceptions, events, constants
│   │   ├── integrations/  # External API clients
│   │   ├── models/   # Database + Pydantic models
│   │   ├── rag/      # RAG pipeline
│   │   ├── services/ # Business logic
│   │   └── utils/    # Logging, metrics, text utils
│   └── tests/
├── frontend/         # Next.js workspace UI
├── docs/             # Documentation
├── infra/            # Docker, K8s configs
└── scripts/          # Utility scripts
```

---

## Multi-Agent System

ResearchOS uses a **deterministic supervisor pattern** — the supervisor routes tasks based on workflow state, not LLM decisions. This ensures auditable, reproducible research workflows.

| Agent | Purpose | LLM |
|-------|---------|-----|
| Supervisor | Deterministic state-based routing | None |
| Research Retrieval | Search academic databases | None (API-only) |
| Literature Review | Synthesize research themes | Kimi (128K context) |
| Citation Verification | Verify DOIs and references | Mistral |
| Gap Analysis | Identify research opportunities | Mistral |
| Methodology Suggestion | Propose research methods | Mistral |
| Draft Writing | Generate paper sections | Kimi (long context) |
| Hallucination Detection | Verify claims against sources | Mistral |
| Formatting | Apply venue-specific formatting | Mistral |
| Journal Recommendation | Match paper to venues | Mistral |
| Reviewer Simulation | Simulate peer review | Kimi |
| Submission Preparation | Package for submission | Mistral |

---

## API Documentation

Once the backend is running, access the interactive API docs at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Development

```bash
# Lint and format
make lint

# Run unit tests
make test-unit

# Run integration tests
make test-integration

# Database migrations
make db-migrate msg="add new table"
make db-upgrade
```

---

## License

MIT

---

<div align="center">
<sub>Built with ❤️ for the research community</sub>
</div>
