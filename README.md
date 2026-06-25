<div align="center">

# 🔬 ResearchOS

### Production-Grade Multi-Agent AI Research Automation Platform

*Powered by LangGraph • Retrieval-Augmented Generation • FastAPI • Next.js • PostgreSQL*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-blue)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?logo=postgresql&logoColor=white)](https://supabase.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20Database-00B388)](https://www.pinecone.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-success)](LICENSE)

</div>

---

# Table of Contents

- Overview
- Why ResearchOS?
- Features
- Architecture
- Tech Stack
- Multi-Agent System
- Project Structure
- Installation
- Deployment
- API
- Roadmap
- License

---

## Overview

ResearchOS is a **production-grade multi-agent AI platform that automates the end-to-end academic research lifecycle—from literature discovery to publication-ready manuscripts—using deterministic workflow orchestration, Retrieval-Augmented Generation (RAG), and specialized AI agents.** 

Unlike simple chatbot wrappers, ResearchOS orchestrates **12 specialized AI agents** through a deterministic supervisor architecture, backed by **real RAG pipelines** with citation grounding, hallucination detection, and verification loops.

---

## Project Status

> 🚧 **Actively Developed**

| Component | Status |
|------------|--------|
| Multi-Agent Workflow | ✅ Complete |
| RAG Pipeline | ✅ Complete |
| Authentication | ✅ Complete |
| PostgreSQL Migration | ✅ Complete |
| Streaming (WebSocket/SSE) | ✅ Complete |
| Docker Support | ✅ Complete |
| Production Deployment | 🚀 In Progress |

---

## Why This Project Stands Out

- 🚀 12-agent deterministic workflow built with LangGraph
- 📚 Retrieval-Augmented Generation using Pinecone
- 🔎 Citation verification and hallucination detection
- ⚡ Real-time workflow visualization with WebSockets
- 🔐 JWT authentication and audit logging
- 🐳 Dockerized production deployment
- ☁️ Railway + Vercel + Supabase architecture

---

## Why ResearchOS?

Most AI research assistants are prompt-based chatbots that struggle with:

- Long-running research workflows
- Citation grounding
- Hallucination control
- Multi-step reasoning
- Workflow reproducibility

ResearchOS addresses these limitations through deterministic workflow orchestration, Retrieval-Augmented Generation (RAG), specialized AI agents, real-time execution monitoring, and production-grade infrastructure.

---

### Key Capabilities

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

## System Components

ResearchOS is composed of five primary layers:

- **Frontend** – Next.js workspace for managing research projects.
- **API Layer** – FastAPI REST APIs, WebSockets and middleware.
- **Workflow Engine** – LangGraph supervisor orchestrating specialized AI agents.
- **Knowledge Layer** – Pinecone vector database with Retrieval-Augmented Generation (RAG).
- **Persistence Layer** – PostgreSQL (Supabase) storing users, projects, workflows, and audit logs.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, Tailwind CSS, shadcn/ui, Framer Motion |
| Backend | Python, FastAPI, SQLAlchemy 2.0 |
| AI Orchestration | LangGraph (supervisor pattern) |
| Vector Database | Pinecone (serverless) |
| Embeddings | BAAI/bge-large-en-v1.5 |
| LLMs | Mistral Large, Kimi (long context) |
| Caching | Redis |
| Database | PostgreSQL (Supabase) |
| Research APIs | arXiv, Semantic Scholar, CrossRef |

---

## Production Features

| Feature | Description |
|----------|-------------|
| JWT Authentication | Secure access & refresh tokens |
| PostgreSQL | Persistent relational storage |
| Pinecone | Semantic vector search |
| Redis | Caching & pub/sub |
| WebSockets | Live workflow updates |
| SSE | Streaming responses |
| Docker | Containerized deployment |
| Gunicorn | Production ASGI server |
| Health Checks | Readiness & liveness endpoints |
| Audit Logging | User action tracking |

---

## Authentication

ResearchOS uses JWT-based authentication with:

- Email/password sign-up

- Email verification

- Password reset

- Short-lived access tokens

- Refresh token support

- Secure password hashing

- JWT authentication

- Role-based authorization

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
git clone https://github.com/TechySan031/ResearchOS.git
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

### backend/

FastAPI backend containing the LangGraph workflow engine, AI agents, REST APIs, WebSocket services, authentication, persistence layer, and integrations.

### frontend/

Next.js application providing the ResearchOS dashboard, research workspace, workflow visualization, and document editor.

### docs/

Architecture diagrams, screenshots, documentation, and deployment assets.

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

After starting the backend:

| Documentation | URL |
|--------------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/api/v1/health |

> Production URLs will be added after deployment.

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


## Deployment

ResearchOS is designed for cloud-native deployment.

| Component | Technology | Platform |
|-----------|------------|----------|
| Frontend | Next.js | Vercel |
| Backend | FastAPI | Railway |
| Database | PostgreSQL | Supabase |
| Vector Database | Pinecone | Serverless |
| Cache | Redis | Railway |

---

## Roadmap

### Completed

- ✅ LangGraph Supervisor
- ✅ 12-Agent Workflow
- ✅ Pinecone Integration
- ✅ PostgreSQL Migration
- ✅ JWT Authentication
- ✅ Audit Logging
- ✅ WebSockets
- ✅ Docker Support

### Upcoming

- 📈 Observability Dashboard
- 🤖 MCP Integration
- 🧠 Local LLM Support
- ☸ Kubernetes Deployment
- 🎥 Live Demo

---

## Future Improvements

- Multi-user collaboration
- Knowledge graph generation
- Citation network visualization
- PDF annotation workspace
- Local LLM support (Ollama)
- Kubernetes deployment
- Distributed agent execution

---

## Engineering Principles

ResearchOS is designed around production software engineering principles:

- Modular architecture
- Asynchronous execution
- Deterministic agent orchestration
- Type-safe APIs
- Scalable service layer
- Secure authentication
- Cloud-native deployment
- Extensible workflow design

---

## License

MIT

---

<div align="center">

### ResearchOS

Production-grade Multi-Agent AI Research Automation Platform

Designed and engineered using modern AI infrastructure, cloud-native architecture, and scalable software engineering practices.

⭐ If you found this project interesting, consider giving it a star!

</div>