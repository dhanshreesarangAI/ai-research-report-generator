# AI Research & Report Generator

A multi-agent pipeline system that takes a complex research request, breaks it into discrete steps, and runs it through a set of specialized agents — built with plain Python and `asyncio` (no black-box agent frameworks).

## What it does

Given a request like:

> "Research the top 5 AI startups, summarize their products, and create a LinkedIn post."

the system:
1. **Plans** — breaks the request into ordered steps
2. **Retrieves** — fetches data for each target (currently mock data; real web search planned)
3. **Analyzes** — summarizes and compares the retrieved data
4. **Writes** — generates a short report and a LinkedIn post
5. **Validates** — checks for missing/incomplete data and triggers a **retry** on just the missing items (up to 2 retries), then gracefully marks anything still missing as "data unavailable" instead of crashing

Partial results are streamed at every stage using an `async generator`, so the user sees progress live instead of waiting for one final output.

## Why no agent framework (e.g. LangChain agents, CrewAI, AutoGen)?

This project is intentionally built with plain Python + `asyncio` to demonstrate a working understanding of agent orchestration mechanics — decomposition, batching, retries, and failure handling — rather than relying on a framework's built-in (and often hidden) implementation of these features.

## Architecture

```
User Request
    │
    ▼
PlannerAgent ──► ordered list of steps
    │
    ▼
RetrieverAgent ──► fetches data in manual batches (asyncio.gather)
    │
    ▼
ValidatorAgent ──► checks for missing fields
    │   └─ if missing → retry RetrieverAgent (max 2 retries)
    ▼
AnalyzerAgent ──► summarizes & compares data
    │
    ▼
WriterAgent ──► generates report + LinkedIn post
    │
    ▼
Streamed output to user (per stage)
```

## Agents

| Agent | Responsibility |
|---|---|
| `PlannerAgent` | Decomposes the user request into an ordered list of steps |
| `RetrieverAgent` | Fetches data per target, in manually-controlled batches |
| `AnalyzerAgent` | Summarizes and compares the retrieved data |
| `WriterAgent` | Generates the final report and LinkedIn post |
| `ValidatorAgent` | Detects missing/incomplete data and drives the retry loop |

## Failure handling

- Each fetch is wrapped in a `try/except` — a failed fetch doesn't crash the pipeline, it returns a placeholder record
- `ValidatorAgent` flags any startup missing required fields (`product`, `funding`)
- The orchestrator retries **only the missing items** (not the whole batch) up to `MAX_RETRIES = 2` times
- If data is still missing after retries, it's clearly labeled `"data unavailable"` in the final report rather than silently failing or crashing

## Running it

```bash
python pipeline.py
```

To see the failure/retry behavior in action, the mock retriever has a configurable `fail_chance` (set in `Orchestrator(fail_chance=0.4)` inside `main()`) that randomly simulates network failures.

## Project status

- [x] Core multi-agent pipeline (mock data)
- [x] Manual batching logic
- [x] Retry-based failure handling
- [x] Streaming partial outputs
- [ ] Real web search integration
- [ ] FastAPI + Server-Sent Events for live web demo

## Author

Dhanshree Sarang
