from __future__ import annotations

import json

from agents.base import Agent
from tools.ats_scorer import score_resume


class BulkResumeAgent(Agent):
    """📚 Пакетная адаптация Tier B (10–20 вакансий за один проход)."""

    name = "bulk-resume"

    def run(self, base_cv_md: str, vacancies: list[dict]) -> dict:
        results: list[dict] = []
        for v in vacancies:
            jid = v.get("id", "job")
            prompt = (
                "Сделай лёгкую (Tier B) адаптацию базового CV под одну вакансию.\n"
                "Целимся ATS-coverage 0.70–0.80.\n\n"
                f"=== Vacancy ===\n{json.dumps(v, ensure_ascii=False, indent=2)}\n=== /Vacancy ===\n\n"
                f"=== Base CV ===\n{base_cv_md}\n=== /Base CV ===\n"
            )
            out = self.ask(prompt, max_tokens=self.max_tokens)
            jd_text = f"{v.get('title','')}\n{v.get('snippet','')}"
            ats = score_resume(out, jd_text)
            cv_path = self.session.write_text(f"resume/tier_b/{jid}/resume.md", out)
            results.append({"id": jid, "resume_path": str(cv_path), "ats_score": ats.score})
        self.session.write_json("resume/tier_b/index.json", results)
        return {"count": len(results), "items": results}
