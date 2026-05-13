from __future__ import annotations

import json

from agents.base import Agent
from tools.web_search import WebSearch


class InterviewCoachAgent(Agent):
    """🎤 Подготовка к интервью: research компании + 25–30 вопросов + STAR-ответы."""

    name = "interview"

    def __init__(self, settings, session):
        super().__init__(settings, session)
        ws_cfg = settings.web_search_cfg()
        self.web = WebSearch(
            providers=ws_cfg.get("providers", ["brave", "tavily", "serper"]),
            results_per_query=int(ws_cfg.get("results_per_query", 6)),
        )

    def research_company(self, company: str, title: str) -> list[dict]:
        queries = [
            f'"{company}" interview process site:glassdoor.com',
            f'"{company}" interview questions site:reddit.com',
            f'"{company}" interview experience site:teamblind.com',
            f'"{company}" "{title}" interview leetcode',
            f'"{company}" engineering blog',
            f'"{company}" news 2026',
        ]
        out: list[dict] = []
        for q in queries:
            try:
                res = self.web.search(q)
            except Exception:
                res = []
            for r in res[:4]:
                out.append({"query": q, **r.to_dict()})
        return out

    def run(self, cv_md: str, strategy_md: str, vacancy: dict | None = None) -> dict:
        evidence: list[dict] = []
        if vacancy:
            evidence = self.research_company(
                vacancy.get("company", ""), vacancy.get("title", "")
            )

        prompt = (
            "Подготовь полный пакет к интервью по системному промпту.\n"
            "Используй research, стратегию и CV. Все нетривиальные утверждения — со ссылками.\n\n"
            f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n\n"
            f"=== CV ===\n{cv_md}\n=== /CV ===\n\n"
            f"=== Vacancy ===\n{json.dumps(vacancy or {}, ensure_ascii=False, indent=2)}\n=== /Vacancy ===\n\n"
            f"=== Research ===\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n=== /Research ===\n"
        )
        out = self.ask(prompt, max_tokens=self.max_tokens)

        jid = (vacancy or {}).get("id", "general")
        path = self.session.write_text(f"interview/{jid}/prep.md", out)
        if evidence:
            self.session.write_json(f"interview/{jid}/research.json", evidence)
        return {"prep_path": str(path), "research_items": len(evidence)}

    def mock_round(self, prep_md: str, user_answer: str) -> str:
        """Один ход mock-интервью."""
        prompt = (
            "Ты ведёшь mock-интервью. Получил ответ клиента — разбери его по структуре STAR,\n"
            "укажи 1–2 фикса, поставь оценку 0..1 и задай следующий вопрос.\n\n"
            f"=== Prep doc ===\n{prep_md}\n=== /Prep doc ===\n\n"
            f"=== Candidate answer ===\n{user_answer}\n=== /Candidate answer ===\n"
        )
        return self.ask(prompt, max_tokens=2000)
