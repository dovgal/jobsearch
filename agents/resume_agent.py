from __future__ import annotations

import json

from agents.base import Agent
from tools.ats_scorer import score_resume


class ResumeAgent(Agent):
    """✏️ Tier-A адаптация под конкретную вакансию."""

    name = "resume"

    def run(self, base_cv_md: str, vacancy: dict) -> dict:
        prompt = (
            "Адаптируй базовое CV под конкретную вакансию Tier A. Каждый булет — под язык JD.\n"
            "Целься в ATS-coverage ≥ 85%.\n\n"
            f"=== Vacancy ===\n{json.dumps(vacancy, ensure_ascii=False, indent=2)}\n=== /Vacancy ===\n\n"
            f"=== Base CV ===\n{base_cv_md}\n=== /Base CV ===\n"
        )
        out = self.ask(prompt, max_tokens=self.max_tokens)

        jd_text = f"{vacancy.get('title','')}\n{vacancy.get('snippet','')}"
        ats = score_resume(out, jd_text)

        jid = vacancy.get("id", "job")
        cv_path = self.session.write_text(f"resume/tier_a/{jid}/resume.md", out)
        self.session.write_json(f"resume/tier_a/{jid}/ats_report.json", ats.to_dict())
        return {"resume_path": str(cv_path), "ats_score": ats.score}
