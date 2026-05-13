from __future__ import annotations

import json
from pathlib import Path

from agents import (
    BaseCVAgent,
    BulkResumeAgent,
    ContentAgent,
    InterviewCoachAgent,
    LinkedInAgent,
    OutreachAgent,
    ResumeAgent,
    StrategyAgent,
    VacancyHunterAgent,
)
from core.session import Session
from core.settings import Settings
from tools.text_io import read_text_file


class Orchestrator:
    def __init__(self, session: Session | None = None, cv_path: Path | str = "input/cv.txt"):
        self.settings = Settings.load()
        self.session = session or Session.open()
        self.cv_path = Path(cv_path)

    # ---------- helpers ----------

    def _require_cv(self) -> str:
        return read_text_file(self.cv_path)

    def _require_strategy(self) -> str:
        p = self.session.recall("strategy_path")
        if not p or not Path(p).exists():
            raise RuntimeError("Сначала запусти strategy-agent: `python main.py strategy`.")
        return Path(p).read_text("utf-8")

    def _require_base_cv(self) -> str:
        p = self.session.recall("base_cv_path")
        if not p or not Path(p).exists():
            raise RuntimeError("Сначала запусти base-cv-agent: `python main.py base-cv`.")
        return Path(p).read_text("utf-8")

    def _load_vacancy(self, job_id: str) -> dict:
        jobs_path = self.session.recall("jobs_path")
        if not jobs_path or not Path(jobs_path).exists():
            raise RuntimeError("Нет jobs.json. Сначала: `python main.py hunt`.")
        jobs = json.loads(Path(jobs_path).read_text("utf-8"))
        for j in jobs:
            if j.get("id") == job_id:
                return j
        raise RuntimeError(f"Вакансия {job_id} не найдена в hunt/jobs.json")

    # ---------- agent runners ----------

    def strategy(self, intake_path: Path | str | None = None) -> dict:
        cv = self._require_cv()
        intake = None
        if intake_path and Path(intake_path).exists():
            intake = json.loads(Path(intake_path).read_text("utf-8"))
        return StrategyAgent(self.settings, self.session).run(cv, intake)

    def base_cv(self) -> dict:
        return BaseCVAgent(self.settings, self.session).run(
            self._require_cv(), self._require_strategy()
        )

    def linkedin(self) -> dict:
        return LinkedInAgent(self.settings, self.session).run(
            self._require_base_cv(), self._require_strategy()
        )

    def hunt(self) -> dict:
        return VacancyHunterAgent(self.settings, self.session).run(self._require_strategy())

    def resume(self, job_id: str) -> dict:
        return ResumeAgent(self.settings, self.session).run(
            self._require_base_cv(), self._load_vacancy(job_id)
        )

    def bulk_resume(self, tier: str = "B") -> dict:
        jobs_path = self.session.recall("jobs_path")
        if not jobs_path:
            raise RuntimeError("Нет jobs.json. Сначала: `python main.py hunt`.")
        jobs = json.loads(Path(jobs_path).read_text("utf-8"))
        targets = [j for j in jobs if (j.get("tier") or "").upper() == tier.upper()]
        return BulkResumeAgent(self.settings, self.session).run(self._require_base_cv(), targets)

    def outreach(self, job_id: str) -> dict:
        return OutreachAgent(self.settings, self.session).run(
            self._load_vacancy(job_id), self._require_base_cv()
        )

    def content(self, voice_samples_path: Path | str | None = None) -> dict:
        voice = ""
        if voice_samples_path and Path(voice_samples_path).exists():
            voice = read_text_file(voice_samples_path)
        return ContentAgent(self.settings, self.session).run(
            self._require_base_cv(), self._require_strategy(), voice
        )

    def interview(self, job_id: str | None = None) -> dict:
        vacancy = self._load_vacancy(job_id) if job_id else None
        return InterviewCoachAgent(self.settings, self.session).run(
            self._require_base_cv(), self._require_strategy(), vacancy
        )

    # ---------- full pipeline ----------

    def full(self, intake_path: Path | str | None = None) -> dict:
        results: dict = {}
        results["strategy"] = self.strategy(intake_path)
        if results["strategy"].get("stage") != "done":
            return results  # ждём intake-ответов
        results["base_cv"] = self.base_cv()
        results["linkedin"] = self.linkedin()
        results["hunt"] = self.hunt()
        return results
