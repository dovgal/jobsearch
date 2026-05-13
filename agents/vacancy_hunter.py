from __future__ import annotations

import json

from agents.base import Agent
from tools.html_renderer import render_vacancies_html
from tools.job_channels import Job, build_channels
from tools.text_io import extract_json_block
from tools.web_search import WebSearch


class VacancyHunterAgent(Agent):
    """🔎 Сборщик и скорер вакансий по множеству каналов."""

    name = "vacancy-hunter"

    def __init__(self, settings, session):
        super().__init__(settings, session)
        ws_cfg = settings.web_search_cfg()
        self.web = WebSearch(
            providers=ws_cfg.get("providers", ["brave", "tavily", "serper"]),
            results_per_query=int(ws_cfg.get("results_per_query", 8)),
        )
        self.per_channel_limit = int(self.agent_cfg.get("per_channel_limit", 50))
        self.score_threshold = float(self.agent_cfg.get("score_threshold", 0.55))

    def derive_queries(self, strategy_md: str) -> list[str]:
        prompt = (
            "На основе стратегии сформируй 8–14 коротких поисковых запросов для job-bord-ов.\n"
            "Каждый запрос — 2–5 слов: роль + ключевая специализация + опц. локация / remote.\n"
            "Ответ — строго JSON-массив строк.\n\n"
            f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n"
        )
        raw = self.ask(prompt, max_tokens=1500)
        data = extract_json_block(raw)
        if isinstance(data, list):
            return [str(q).strip() for q in data if str(q).strip()][:14]
        return [l.lstrip("-•* ").strip() for l in raw.splitlines() if l.strip()][:14]

    def harvest(self, queries: list[str]) -> list[Job]:
        channels = build_channels(self.settings.job_channels(), self.web)
        jobs: list[Job] = []
        for ch in channels:
            try:
                got = ch.search(queries, limit=self.per_channel_limit)
            except Exception:
                got = []
            jobs.extend(got)
        seen, uniq = set(), []
        for j in jobs:
            if j.id in seen:
                continue
            seen.add(j.id)
            uniq.append(j)
        return uniq

    def score(self, jobs: list[Job], strategy_md: str) -> list[dict]:
        scored: list[dict] = []
        batch_size = 8
        for i in range(0, len(jobs), batch_size):
            chunk = jobs[i : i + batch_size]
            payload = [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "salary": j.salary,
                    "source": j.source,
                    "snippet": j.snippet[:600],
                }
                for j in chunk
            ]
            prompt = (
                "Оцени вакансии по 12 параметрам согласно системному промпту.\n\n"
                f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n\n"
                f"=== Vacancies ===\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n=== /Vacancies ===\n"
            )
            raw = self.ask(prompt, max_tokens=4000, temperature=0.2)
            parsed = extract_json_block(raw)
            if isinstance(parsed, list):
                scored.extend(parsed)
        return scored

    def merge_and_render(self, jobs: list[Job], scores: list[dict]) -> dict:
        by_id = {s.get("id"): s for s in scores if isinstance(s, dict)}
        enriched: list[dict] = []
        for j in jobs:
            s = by_id.get(j.id) or {}
            d = j.to_dict()
            d["score"] = float(s.get("score") or 0.0)
            d["tier"] = s.get("tier") or "skip"
            d["score_reasons"] = s.get("score_reasons") or []
            d["warnings"] = s.get("warnings") or []
            d["scores"] = s.get("scores") or {}
            enriched.append(d)

        enriched.sort(key=lambda x: x["score"], reverse=True)
        visible = [e for e in enriched if e["score"] >= self.score_threshold]

        json_path = self.session.write_json("hunt/jobs.json", enriched)
        html_path = self.session.root / "hunt" / "vacancies.html"
        render_vacancies_html(visible, html_path, title="Vacancy review")

        self.session.remember("jobs_path", str(json_path))
        self.session.remember("vacancies_html", str(html_path))

        return {
            "total_collected": len(jobs),
            "above_threshold": len(visible),
            "html_path": str(html_path),
            "json_path": str(json_path),
        }

    def run(self, strategy_md: str) -> dict:
        queries = self.derive_queries(strategy_md)
        self.session.write_json("hunt/queries.json", queries)

        jobs = self.harvest(queries)
        self.session.write_json("hunt/raw_jobs.json", [j.to_dict() for j in jobs])

        scores = self.score(jobs, strategy_md) if jobs else []
        self.session.write_json("hunt/scores.json", scores)

        return self.merge_and_render(jobs, scores)
