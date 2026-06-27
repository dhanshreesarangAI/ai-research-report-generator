# Post-Mortem
## AI Research & Report Generator

### 1. Scaling Issue

**Issue: Sequential batch processing limits throughput as the number of targets grows.**

The current `RetrieverAgent` processes targets in fixed-size batches (e.g. 2 at a time), running each batch concurrently but running batches themselves one after another. For 5 targets this is fine, but if the system were asked to research 200 startups instead of 5, the total time would scale roughly linearly with the number of batches, since there's no concurrency *across* batches — only within one.

At larger scale, this would also start hitting rate limits on a real search API (if/when mock data is replaced with a real one), since a fixed batch size doesn't adapt to how many requests the API allows per second. A production version would need adaptive batching (adjusting batch size or delay based on API response headers/rate-limit signals) and a job queue rather than a single in-memory loop, so retrieval work could be distributed and resumed if the process restarted mid-run.

### 2. Design Change in Hindsight

**Change: I would decouple the retry logic from the Orchestrator and make it a property of the RetrieverAgent itself.**

Currently, the Orchestrator owns the retry loop — it calls the Retriever, checks with the Validator, and decides whether to retry. This works, but it means the Orchestrator has to know retrieval-specific details (like "retry only the missing names") rather than just calling agents and trusting each one to return its best possible result.

In hindsight, I'd push retry-with-backoff logic *into* `RetrieverAgent.run()` itself, so it internally retries failed fetches before ever returning to the Orchestrator. The Orchestrator would then only handle a higher-level retry (e.g., "the whole stage failed validation, try the stage again"), which would keep each agent more self-contained and make the Orchestrator's logic simpler and more reusable for future agents.

### 3. Trade-offs

**Trade-off 1: Manual batching/asyncio vs. an existing agent framework**

*Choice made:* Plain Python + `asyncio`, no LangChain/CrewAI/AutoGen agent executor.

*Reasoning:* The assignment explicitly required understanding what happens "under the hood," and a framework's `AgentExecutor` would have hidden the batching, retry, and streaming logic I needed to demonstrate. The trade-off is that this version has fewer built-in features (no automatic tool-calling, no memory management, no built-in observability) that a framework like LangChain would provide for free. For a real production system with many more agent types, a framework might reduce boilerplate — but for this assignment's goal of demonstrating orchestration understanding, writing it manually was the right call.

**Trade-off 2: Mock data first vs. real web search from the start**

*Choice made:* Build and test the full pipeline against mock data before integrating a real search API.

*Reasoning:* This let me validate the orchestration logic (decomposition, batching, retry, streaming, failure handling) quickly and deterministically, without spending time debugging API keys, rate limits, or inconsistent real-world data while also debugging my own pipeline code. The trade-off is that the current demo doesn't yet prove the system works against messy, unpredictable real data — error modes from a real API (timeouts, malformed responses, partial JSON) may differ from the simple `ConnectionError` simulated here, so some failure-handling logic may need to be extended once real search is integrated.
