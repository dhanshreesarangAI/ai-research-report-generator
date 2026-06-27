# System Design Document
## AI Research & Report Generator

### 1.Overview 

This system accepts a single, complex user request (e.g. "Research the top 5 AI startups, summarize their products, and create a LinkedIn post") and processes it through a pipeline of specialized agents, each responsible for one part of the task. The system is built in plain Python using `asyncio`, without relying on a black-box agent framework, so that the orchestration logic — decomposition, batching, retries, and failure handling — is fully visible and explainable.

### 2.Architecture

```
                    ┌─────────────────┐
                    │  User request  │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │  PlannerAgent   │  breaks request into ordered steps 
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
              ┌────►│ RetrieverAgent  │  fetches data in manual batches
              │     └────────┬────────┘
              │              ▼
              │     ┌─────────────────┐
              │     │ ValidatorAgent  │  check for missing fields
              │     └────────┬────────┘
              │              │
       retry  └──────────────┤ missing data found (max 2 retries)
     (only missing items)    │
                              ▼ no missing data / retries exhausted
                    ┌─────────────────┐
                    │  AnalyzerAgent  │  summarizes & compares data
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │   WriterAgent   │  generates report + LinkedIn post
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ Streamed Output │  each stage yielded to the user
                    └─────────────────┘
```

### 3.Components

**PlannerAgent**
Takes the raw user request and produces an ordered list of steps as structured data (a list of dicts). In the current version, decomposition logic is explicit and rule-based rather than LLM-generated, so the breakdown is deterministic and easy to verify. This could be swapped for an LLM call that returns the same JSON shape, without changing any other part of the system.

**RetrieverAgent**
Responsible for fetching data per target (currently from a mock dataset; designed to be swapped for a real search API). Implements **manual batching**: targets are split into fixed-size chunks (`batch_size`), and each chunk is fetched concurrently using `asyncio.gather`. This was written explicitly rather than relying on a framework's built-in batching utility, so the batching behavior (chunk size, concurrency, ordering) is fully visible and tunable.

**ValidatorAgent**
Inspects each retrieved record against a list of required fields (`product`, `funding`). Returns the names of any records missing required data. This agent contains no retrieval or writing logic — its only job is detection.

**AnalyzerAgent**
Takes the (possibly incomplete) list of retrieved records and produces a summary: counts of complete/incomplete records and a structured comparison. This stage does not know how the data was retrieved or whether retries occurred — it works only with whatever data it's given.

**WriterAgent**
Converts the analysis into two final outputs: a short markdown report and a LinkedIn-style post. Any data marked as missing is rendered as "Data unavailable" rather than omitted, so the report is transparent about its own limitations.

**Orchestrator**
The coordinating layer. It is not itself an "agent" with domain logic — its job is purely to:
- call agents in the correct order
- pass each agent's output as the next agent's input
- run the Retriever → Validator retry loop
- `yield` partial results after each stage so the caller can stream progress

### 4.Data Flow

1. User request (string) → `PlannerAgent` → list of step dicts
2. Step dict targets → `RetrieverAgent` → list of record dicts (some possibly incomplete)
3. Record list → `ValidatorAgent` → list of missing record names
4. If missing names is non-empty and retry budget remains → re-run `RetrieverAgent` on only the missing names → merge results back into the main record list → re-validate
5. Final record list (with any still-missing items left as `None` fields) → `AnalyzerAgent` → analysis dict
6. Analysis dict → `WriterAgent` → `{report, linkedin_post}`
7. Each of steps 2, 4 (final), 5, 6 is `yield`ed to the caller as it completes, plus a final `done` event summarizing whether all data was resolved

### 5.Concurrency model

The system uses `asyncio` throughout. Within a single batch, multiple retrieval calls run concurrently via `asyncio.gather`; batches themselves run sequentially to keep concurrency bounded and predictable. This is a deliberate, simple concurrency model — not the most parallel possible, but one whose behavior is easy to reason about and explain.

### 6.Failure handling

- Each individual fetch is wrapped in a `try/except`. A failed fetch does not raise out of the pipeline — it returns a placeholder record with an `error` field.
- The Validator/retry loop targets **only** the specific items that failed or are incomplete, not the entire batch — this avoids wasted work re-fetching data that already succeeded.
- A hard retry limit (`MAX_RETRIES = 2`) prevents infinite retry loops.
- If data is still missing after retries are exhausted, the system does not fail the whole pipeline — it proceeds to the Writer/Analyzer stages with the data it has, and clearly marks the gaps in the final output (`"Data unavailable"`, and a `success: false` flag in the final `done` event).

### 7.Streaming

The `Orchestrator.run()` method is implemented as an `async generator` (using `yield` inside an `async def`). This allows the caller to iterate over results with `async for` and receive each stage's output as soon as it's ready, rather than waiting for the entire pipeline to finish. This same generator can be connected to a CLI print loop (current implementation) or to a web layer (e.g. FastAPI with Server-Sent Events) without changing the core pipeline logic.

### 8.Current limitations / planned extensions

- Retrieval currently uses mock data; real web search integration is planned as a drop-in replacement for `mock_search()`.
- The system currently runs as a CLI/notebook script; a FastAPI + SSE wrapper is planned to expose the same streaming behavior over HTTP for a live browser demo.
