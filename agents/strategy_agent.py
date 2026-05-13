from __future__ import annotations

import json

from agents.base import Agent
from llm import Message
from tools.text_io import extract_json_block
from tools.web_search import SearchResult, WebSearch


class StrategyAgent(Agent):
    """🎯 Стратегия поиска работы."""

    name = "strategy"

    def __init__(self, settings, session):
        super().__init__(settings, session)
        ws_cfg = settings.web_search_cfg()
        self.web = WebSearch(
            providers=ws_cfg.get("providers", ["brave", "tavily", "serper"]),
            results_per_query=int(ws_cfg.get("results_per_query", 8)),
        )
        self.web_queries_target = int(self.agent_cfg.get("web_search_queries", 20))

    def generate_questions(self, cv_text: str) -> list[str]:
        prompt = (
            "Прочитай резюме клиента и сформируй 15+ уточняющих вопросов как карьерный коуч.\n"
            "Вопросы должны вытаскивать: реальный уровень, желаемые роли, "
            "географию, ограничения, неназванные достижения с цифрами, мотивацию.\n"
            "Не задавай поверхностных вопросов вроде 'какие у тебя сильные стороны?'. "
            "Каждый вопрос — конкретный, требующий конкретного ответа.\n\n"
            "Ответ — строго JSON-массив строк. Без прозы.\n\n"
            f"=== CV ===\n{cv_text}\n=== /CV ===\n"
        )
        raw = self.ask(prompt, max_tokens=3000)
        data = extract_json_block(raw)
        if isinstance(data, list):
            return [str(q).strip() for q in data if str(q).strip()]
        return [line.lstrip("-•* ").strip() for line in raw.splitlines() if line.strip()][:25]

    def generate_search_queries(self, cv_text: str, intake: dict) -> list[str]:
        prompt = (
            f"Сгенерируй {self.web_queries_target}+ конкретных запросов в Google/Brave/Tavily,\n"
            "которые соберут свежие данные по индустрии, региону, зарплатам, трендам и компаниям\n"
            "под профиль клиента. Запросы должны быть точными (с годом, городом, конкретными отчётами).\n"
            "Ответ — строго JSON-массив строк.\n\n"
            f"=== CV ===\n{cv_text}\n=== /CV ===\n\n"
            f"=== Intake answers ===\n{json.dumps(intake, ensure_ascii=False, indent=2)}\n=== /Intake ===\n"
        )
        raw = self.ask(prompt, max_tokens=3000, temperature=0.5)
        data = extract_json_block(raw)
        if isinstance(data, list):
            return [str(q).strip() for q in data if str(q).strip()][: self.web_queries_target * 2]
        return [line.lstrip("-•* ").strip() for line in raw.splitlines() if line.strip()][: self.web_queries_target]

    def collect_evidence(self, queries: list[str]) -> dict[str, list[dict]]:
        evidence: dict[str, list[dict]] = {}
        for q in queries:
            try:
                results: list[SearchResult] = self.web.search(q)
            except Exception:
                results = []
            evidence[q] = [r.to_dict() for r in results]
        return evidence

    def write_strategy(self, cv_text: str, intake: dict, evidence: dict) -> str:
        bib_lines: list[str] = []
        n = 1
        for q, results in evidence.items():
            for r in results[:4]:
                bib_lines.append(f"[{n}] {r.get('title', '')} — {r.get('url', '')}")
                bib_lines.append(f"    snippet: {r.get('snippet', '')[:240]}")
                n += 1
        bib = "\n".join(bib_lines)

        prompt = (
            "Используй CV, ответы клиента и собранные web-источники, чтобы написать стратегию.\n"
            "Минимум 500 строк markdown. Все утверждения про рынок и зарплаты подкрепляй ссылками [N].\n\n"
            f"=== CV ===\n{cv_text}\n=== /CV ===\n\n"
            f"=== Intake ===\n{json.dumps(intake, ensure_ascii=False, indent=2)}\n=== /Intake ===\n\n"
            f"=== Web evidence (bibliography) ===\n{bib}\n=== /Web evidence ===\n"
        )
        return self.ask(prompt, max_tokens=self.max_tokens)

    def run(self, cv_text: str, intake_answers: dict | None = None) -> dict:
        questions = self.generate_questions(cv_text)
        self.session.write_json("strategy/coaching_questions.json", questions)

        if intake_answers is None:
            return {
                "stage": "awaiting_intake",
                "questions": questions,
                "hint": "Заполните output/<session>/strategy/intake_answers.json и перезапустите.",
            }

        self.session.write_json("strategy/intake_answers.json", intake_answers)

        queries = self.generate_search_queries(cv_text, intake_answers)
        self.session.write_json("strategy/search_queries.json", queries)

        evidence = self.collect_evidence(queries)
        self.session.write_json("strategy/evidence.json", evidence)

        strategy_md = self.write_strategy(cv_text, intake_answers, evidence)
        path = self.session.write_text("strategy/strategy.md", strategy_md)

        self.session.remember("strategy_path", str(path))
        return {
            "stage": "done",
            "questions": questions,
            "queries": queries,
            "evidence_sources": sum(len(v) for v in evidence.values()),
            "strategy_path": str(path),
        }
