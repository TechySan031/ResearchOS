# ResearchOS — Agent Design Documentation

## Overview

ResearchOS uses a **supervisor-based multi-agent architecture** built on LangGraph. The supervisor agent uses **deterministic routing** (not LLM-based) to coordinate 12 specialized agents through a research workflow.

## Agent State

All agents share a single `ResearchState` TypedDict. Each agent reads relevant fields, performs its task, and returns state updates. The supervisor inspects the state to determine the next agent.

## Agent Lifecycle

```
1. Supervisor inspects state
2. Supervisor routes to next agent (deterministic)
3. Agent receives state
4. Agent publishes "started" event
5. Agent executes (may call tools, LLMs, RAG)
6. Agent publishes "progress" events
7. Agent returns state updates
8. Agent publishes "completed" event
9. State is merged
10. Control returns to supervisor
```

## Revision Loops

Two feedback loops exist in the workflow:

### Hallucination Loop
- After draft writing, hallucination detection agent scores the draft
- If hallucination_score > 0.3, the draft is sent back for revision
- Maximum 3 revision cycles
- Each revision receives specific feedback on problematic claims

### Reviewer Loop
- After formatting, the reviewer simulation agent evaluates the paper
- If review score < 6/10, the draft is sent back for revision
- Maximum 2 revision cycles
- Reviewer feedback is structured (strengths, weaknesses, suggestions)

## Adding New Agents

1. Create agent node in `backend/app/agents/nodes/`
2. Create agent prompt in `backend/app/agents/prompts/`
3. Add agent name to `AgentName` enum
4. Add node to graph in `backend/app/agents/graph.py`
5. Add routing rule in `backend/app/agents/supervisor.py`
6. Update `ResearchState` if new state fields are needed
