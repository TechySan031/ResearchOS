# ResearchOS — Architecture Documentation

## System Architecture

See [implementation_plan.md](../../implementation_plan.md) for the complete architecture design.

## Key Architectural Decisions

### 1. Deterministic Supervisor vs LLM-Based Routing

We use **deterministic state-machine routing** in the supervisor agent, NOT LLM-based routing.

**Rationale:**
- Research workflows must be **reproducible** — same input should produce same execution path
- LLM routing introduces non-determinism and hallucination risk at the workflow level
- Debugging is trivial — every routing decision is a pure function of state
- LLM creativity is applied **within** each agent's task, not to workflow orchestration

### 2. Dual-LLM Strategy

We use two LLMs for different purposes:
- **Kimi (moonshot-v1-128k)**: Long-context tasks (literature review, drafting, reviewer simulation)
- **Mistral (mistral-large)**: Structured generation (verification, formatting, gap analysis)

**Rationale:**
- No single model excels at everything
- Kimi's 128K context is essential for synthesizing 20+ papers
- Mistral's structured output is better for verification tasks
- Dual-model reduces single-provider dependency risk

### 3. PostgreSQL + Pinecone (Not Just Pinecone)

- **PostgreSQL**: Relational data (users, projects, papers, citations, agent logs)
- **Pinecone**: Vector search index only

**Rationale:**
- Pinecone is NOT a relational database — it can't do JOINs, transactions, or complex queries
- Pinecone metadata is limited to 40KB per vector
- PostgreSQL is the source of truth; Pinecone is a search index

### 4. WebSocket + SSE (Not Just WebSocket)

- **WebSocket**: Bidirectional agent status events
- **SSE**: Unidirectional LLM token streaming

**Rationale:**
- Agent status updates need bidirectional communication (client can send control commands)
- LLM token streaming is unidirectional — SSE is simpler and more reliable for this
- Separation of concerns: status ≠ content

### 5. asyncio + Redis Over Celery

For Phase 1-5, we use native asyncio with Redis pub-sub instead of Celery.

**Rationale:**
- LangGraph workflows are async-native
- Celery adds significant complexity (broker, worker, beat)
- Celery has serialization issues with complex LangGraph state
- asyncio is sufficient for < 1000 concurrent workflows
- Celery can be added in Phase 6+ if scale demands it
