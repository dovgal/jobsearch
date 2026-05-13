from __future__ import annotations

import json

from agents.base import Agent
from tools.web_search import WebSearch


class OutreachAgent(Agent):
    """🤝 Research hiring manager / recruiter + персональные сообщения."""

    name = "outreach"

    def __init__(self, settings, session):
        super().__init__(settings, session)
        ws_cfg = settings.web_search_cfg()
        self.web = WebSearch(
            providers=ws_cfg.get("providers", ["brave", "tavily", "serper"]),
            results_per_query=int(ws_cfg.get("results_per_query", 6)),
        )

    def research_contact(self, vacancy: dict) -> list[dict]:
        company = vacancy.get("company", "")
        title_hint = vacancy.get("title", "")
        queries = [
            f'"{company}" "hiring manager" {title_hint}',
            f'"{company}" "talent acquisition" OR recruiter site:linkedin.com/in',
            f'"{company}" engineering manager site:linkedin.com/in',
            f'"{company}" news 2026',
        ]
        evidence: list[dict] = []
        for q in queries:
            try:
                results = self.web.search(q)
            except Exception:
                results = []
            for r in results[:5]:
                evidence.append({"query": q, **r.to_dict()})
        return evidence

    def run(self, vacancy: dict, base_cv_md: str) -> dict:
        evidence = self.research_contact(vacancy)

        prompt = (
            "Подготовь outreach-кампанию (initial + 2 follow-up) для конкретной вакансии.\n"
            "Используй research-факты ниже — каждый hook должен ссылаться на конкретный артефакт.\n\n"
            f"=== Vacancy ===\n{json.dumps(vacancy, ensure_ascii=False, indent=2)}\n=== /Vacancy ===\n\n"
            f"=== Candidate CV ===\n{base_cv_md}\n=== /Candidate CV ===\n\n"
            f"=== Research ===\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n=== /Research ===\n"
        )
        out = self.ask(prompt, max_tokens=self.max_tokens)

        jid = vacancy.get("id", "job")
        path = self.session.write_text(f"outreach/{jid}/messages.md", out)
        self.session.write_json(f"outreach/{jid}/research.json", evidence)
        return {"outreach_path": str(path), "research_items": len(evidence)}
