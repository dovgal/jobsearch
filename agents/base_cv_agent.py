from __future__ import annotations

from agents.base import Agent
from tools.ats_scorer import score_resume


class BaseCVAgent(Agent):
    """📄 Базовое CV под стратегическое позиционирование."""

    name = "base-cv"

    def __init__(self, settings, session):
        super().__init__(settings, session)
        self.target_score = float(self.agent_cfg.get("ats_target_score", 0.85))

    def run(self, cv_text: str, strategy_md: str) -> dict:
        prompt = (
            "Перепиши базовое CV клиента под позиционирование из стратегии.\n"
            "Подними iceberg-достижения. ATS-ключевики из стратегии распредели естественно.\n"
            "Цель — ATS-score ≥ 0.85.\n\n"
            f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n\n"
            f"=== CV (raw) ===\n{cv_text}\n=== /CV ===\n"
        )
        cv_md = self.ask(prompt, max_tokens=self.max_tokens)

        report = score_resume(cv_md, strategy_md)
        if report.score < self.target_score and report.missing_keywords:
            refine_prompt = (
                "Текущая ATS-coverage базового CV ниже целевой. Не выдумывай опыта, "
                "но перефразируй существующие булеты так, чтобы естественно появились "
                "следующие ключевики (только те, что реально относятся к опыту клиента):\n"
                f"{', '.join(report.missing_keywords[:30])}\n\n"
                "Верни обновлённый markdown резюме целиком.\n\n"
                f"=== Current CV ===\n{cv_md}\n=== /Current CV ===\n"
            )
            cv_md = self.ask(refine_prompt, max_tokens=self.max_tokens)
            report = score_resume(cv_md, strategy_md)

        cv_path = self.session.write_text("base_cv/base_cv.md", cv_md)
        self.session.write_json("base_cv/ats_report.json", report.to_dict())
        self.session.remember("base_cv_path", str(cv_path))

        return {
            "cv_path": str(cv_path),
            "ats_score": report.score,
            "matched_keywords": report.matched_keywords[:30],
            "missing_keywords": report.missing_keywords[:30],
        }
