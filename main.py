from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.panel import Panel

from core.session import Session
from pipeline.orchestrator import Orchestrator

app = typer.Typer(
    add_completion=False,
    help="Job-search consultation — мульти-агентный пайплайн.",
    no_args_is_help=True,
)


def _orc(session_id: Optional[str], cv_path: str) -> Orchestrator:
    session = Session.open(session_id) if session_id else Session.open()
    return Orchestrator(session=session, cv_path=cv_path)


def _pp(result: dict) -> None:
    print(Panel.fit(json.dumps(result, ensure_ascii=False, indent=2), border_style="cyan"))


@app.command("strategy")
def cmd_strategy(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt", help="Путь к CV клиента"),
    intake: Optional[str] = typer.Option(None, "--intake", help="JSON с ответами клиента"),
):
    """🎯 Стратегия (intake-вопросы → web-research → стратегия ≥500 строк)."""
    res = _orc(session_id, cv).strategy(intake)
    _pp(res)


@app.command("base-cv")
def cmd_base_cv(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """📄 Базовое CV под стратегическое позиционирование."""
    _pp(_orc(session_id, cv).base_cv())


@app.command("linkedin")
def cmd_linkedin(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """💼 LinkedIn-профиль (headline + about + experience + skills)."""
    _pp(_orc(session_id, cv).linkedin())


@app.command("hunt")
def cmd_hunt(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """🔎 Сканирование каналов вакансий + интерактивный HTML."""
    _pp(_orc(session_id, cv).hunt())


@app.command("resume")
def cmd_resume(
    job_id: str = typer.Argument(..., help="id вакансии из hunt/jobs.json"),
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """✏️ Глубокая адаптация резюме под одну Tier A вакансию."""
    _pp(_orc(session_id, cv).resume(job_id))


@app.command("bulk-resume")
def cmd_bulk_resume(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
    tier: str = typer.Option("B", help="Какой tier обрабатывать (A/B/C)"),
):
    """📚 Пакетная адаптация под Tier B (десятки штук)."""
    _pp(_orc(session_id, cv).bulk_resume(tier))


@app.command("outreach")
def cmd_outreach(
    job_id: str = typer.Argument(...),
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """🤝 Research + персонализированные сообщения hiring-менеджерам."""
    _pp(_orc(session_id, cv).outreach(job_id))


@app.command("content")
def cmd_content(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
    voice: Optional[str] = typer.Option(None, "--voice", help="Файл с образцами текстов клиента"),
):
    """📝 LinkedIn-посты в tone of voice клиента."""
    _pp(_orc(session_id, cv).content(voice))


@app.command("interview")
def cmd_interview(
    job_id: Optional[str] = typer.Argument(None),
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
):
    """🎤 Подготовка к интервью (research + 25–30 вопросов + STAR)."""
    _pp(_orc(session_id, cv).interview(job_id))


@app.command("full")
def cmd_full(
    session_id: Optional[str] = typer.Option(None, "--session"),
    cv: str = typer.Option("input/cv.txt"),
    intake: Optional[str] = typer.Option(None, "--intake"),
):
    """Полный пайплайн: strategy → base-cv → linkedin → hunt."""
    _pp(_orc(session_id, cv).full(intake))


@app.command("sessions")
def cmd_sessions():
    """Список всех сессий в output/."""
    root = Path("output")
    if not root.exists():
        print("No sessions yet.")
        return
    for p in sorted(root.iterdir(), reverse=True):
        if p.is_dir():
            print(f"  {p.name}")


if __name__ == "__main__":
    app()
