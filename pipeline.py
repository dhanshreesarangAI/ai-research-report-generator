import asyncio
import random
import json


MOCK_DATABASE = {
    "Startup A": {"product": "AI-powered customer support bot", "funding": "$5M Series A"},
    "Startup B": {"product": "Computer vision for retail analytics", "funding": "$2M Seed"},
    "Startup C": {"product": "LLM-based legal document review", "funding": None},
    "Startup D": {"product": "Voice AI for healthcare scheduling", "funding": "$8M Series A"},
    "Startup E": {"product": None, "funding": "$1.5M Seed"},
}


async def mock_search(name, fail_chance=0.4):
    await asyncio.sleep(0.3)
    if random.random() < fail_chance:
        raise ConnectionError(f"Simulated network failure while fetching '{name}'")
    record = MOCK_DATABASE.get(name, {})
    return {"name": name, "product": record.get("product"), "funding": record.get("funding")}


class PlannerAgent:
    async def run(self, user_request):
        startup_names = list(MOCK_DATABASE.keys())[:5]
        plan = [
            {"step": 1, "agent": "Retriever", "task": "fetch_data", "targets": startup_names},
            {"step": 2, "agent": "Analyzer", "task": "summarize_and_compare"},
            {"step": 3, "agent": "Writer", "task": "generate_report_and_post"},
            {"step": 4, "agent": "Validator", "task": "check_completeness"},
        ]
        return plan


class RetrieverAgent:
    def __init__(self, batch_size=2, fail_chance=0.0):
        self.batch_size = batch_size
        self.fail_chance = fail_chance

    async def run(self, names):
        results = []
        for i in range(0, len(names), self.batch_size):
            batch = names[i:i + self.batch_size]
            print(f"  [Retriever] fetching batch: {batch}")
            batch_tasks = [self._safe_fetch(name) for name in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        return results

    async def _safe_fetch(self, name):
        try:
            return await mock_search(name, fail_chance=self.fail_chance)
        except ConnectionError as e:
            print(f"  [Retriever] ⚠️ fetch failed for '{name}': {e}")
            return {"name": name, "product": None, "funding": None, "error": str(e)}


class AnalyzerAgent:
    async def run(self, startups):
        await asyncio.sleep(0.2)
        funded = [s for s in startups if s.get("funding")]
        unfunded = [s for s in startups if not s.get("funding")]
        return {
            "total_startups": len(startups),
            "with_funding_info": len(funded),
            "missing_funding_info": [s["name"] for s in unfunded],
            "startups": startups,
        }


class WriterAgent:
    async def run(self, analysis):
        await asyncio.sleep(0.2)
        lines = ["# AI Startups Report\n"]
        for s in analysis["startups"]:
            product = s.get("product") or "Data unavailable"
            funding = s.get("funding") or "Data unavailable"
            lines.append(f"- **{s['name']}**: {product} (Funding: {funding})")
        report = "\n".join(lines)
        linkedin_post = (
            f"🚀 Just researched {analysis['total_startups']} AI startups! "
            f"{analysis['with_funding_info']} had clear funding data. "
            f"Exciting times in the AI space. #AI #Startups #India"
        )
        return {"report": report, "linkedin_post": linkedin_post}


class ValidatorAgent:
    REQUIRED_FIELDS = ["product", "funding"]

    def find_missing(self, startups):
        missing = []
        for s in startups:
            for field in self.REQUIRED_FIELDS:
                if not s.get(field):
                    missing.append(s["name"])
                    break
        return missing


class Orchestrator:
    MAX_RETRIES = 2

    def __init__(self, fail_chance=0.0):
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent(batch_size=2, fail_chance=fail_chance)
        self.analyzer = AnalyzerAgent()
        self.writer = WriterAgent()
        self.validator = ValidatorAgent()

    async def run(self, user_request):
        print(f"\n🧠 USER REQUEST: {user_request}\n")

        plan = await self.planner.run(user_request)
        yield {"stage": "plan", "data": plan}
        targets = plan[0]["targets"]

        data = await self.retriever.run(targets)
        attempts = 0
        missing = self.validator.find_missing(data)

        while missing and attempts < self.MAX_RETRIES:
            print(f"\n⚠️  Missing data for: {missing}. Retry {attempts + 1}/{self.MAX_RETRIES}...")
            retry_results = await self.retriever.run(missing)
            retry_map = {r["name"]: r for r in retry_results}
            data = [retry_map.get(s["name"], s) for s in data]
            attempts += 1
            missing = self.validator.find_missing(data)

        if missing:
            print(f"\n❌ Still missing after {self.MAX_RETRIES} retries: {missing}. Marking as 'data unavailable'.")

        yield {"stage": "retrieve", "data": data, "unresolved_missing": missing}

        analysis = await self.analyzer.run(data)
        yield {"stage": "analyze", "data": analysis}

        output = await self.writer.run(analysis)
        yield {"stage": "write", "data": output}

        yield {"stage": "done", "data": {"success": len(missing) == 0, "unresolved": missing}}


async def main():
    orchestrator = Orchestrator(fail_chance=0.4)
    user_request = "Research the top 5 AI startups, summarize their products, and create a LinkedIn post."

    async for partial in orchestrator.run(user_request):
        print(f"\n--- STREAMED UPDATE: [{partial['stage'].upper()}] ---")
        print(json.dumps(partial["data"], indent=2, default=str))

    print("\n✅ Pipeline complete.\n")


await main()
