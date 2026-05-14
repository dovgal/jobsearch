from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.session import Session
from core.settings import Settings
from pipeline.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
OUTPUT_DIR = REPO_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Job Search Consultation", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---------------------------------------------------------------------------
# Background task registry
# ---------------------------------------------------------------------------

_tasks: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _set_task(task_id: str, data: dict) -> None:
    with _lock:
        _tasks[task_id] = data


def _get_task(task_id: str) -> dict:
    with _lock:
        return _tasks.get(task_id, {"status": "unknown"})


def _start(task_id: str, fn, *args, **kwargs) -> None:
    _set_task(task_id, {"status": "running"})

    def _run():
        try:
            result = fn(*args, **kwargs)
            _set_task(task_id, {"status": "done", "result": result})
        except Exception as exc:
            _set_task(task_id, {"status": "error", "error": str(exc)})

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session(sid: str) -> Session:
    return Session.open(sid, base_dir=str(OUTPUT_DIR))


def _cv_path(sid: str) -> Path:
    return OUTPUT_DIR / sid / "input_cv.txt"


def _session_ctx(sid: str) -> dict:
    """Build template context from session state."""
    session = _session(sid)
    state = session.state
    cv_text = _cv_path(sid).read_text("utf-8") if _cv_path(sid).exists() else ""

    def _exists(key: str) -> bool:
        p = state.get(key)
        return bool(p and Path(p).exists())

    questions_path = OUTPUT_DIR / sid / "strategy" / "coaching_questions.json"
    questions = (
        json.loads(questions_path.read_text("utf-8"))
        if questions_path.exists()
        else []
    )
    intake_path = OUTPUT_DIR / sid / "strategy" / "intake_answers.json"
    has_intake = intake_path.exists()

    jobs: list[dict] = []
    if _exists("jobs_path"):
        jobs = json.loads(Path(state["jobs_path"]).read_text("utf-8"))

    return {
        "sid": sid,
        "cv_preview": cv_text[:400] + ("…" if len(cv_text) > 400 else ""),
        "state": state,
        "has_strategy": _exists("strategy_path"),
        "has_base_cv": _exists("base_cv_path"),
        "has_linkedin": _exists("linkedin_path"),
        "has_jobs": _exists("jobs_path"),
        "questions": questions,
        "has_intake": has_intake,
        "jobs": [j for j in jobs if (j.get("tier") or "skip") != "skip"][:30],
    }


# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sessions = []
    for p in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        state = {}
        state_file = p / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text("utf-8"))
        sessions.append({
            "id": p.name,
            "has_strategy": bool(state.get("strategy_path")),
            "has_jobs": bool(state.get("jobs_path")),
        })
    return templates.TemplateResponse("home.html", {"request": request, "sessions": sessions[:10]})


@app.post("/session/new")
async def new_session(cv_text: str = Form(""), cv_file: Optional[UploadFile] = None):
    if cv_file and cv_file.filename:
        content = (await cv_file.read()).decode("utf-8", errors="ignore").strip()
    else:
        content = cv_text.strip()

    if not content:
        return RedirectResponse("/", status_code=303)

    session = Session.open(base_dir=str(OUTPUT_DIR))
    _cv_path(session.session_id).write_text(content, "utf-8")
    return RedirectResponse(f"/session/{session.session_id}", status_code=303)


@app.get("/session/{sid}", response_class=HTMLResponse)
async def session_page(request: Request, sid: str):
    ctx = _session_ctx(sid)
    ctx["request"] = request
    return templates.TemplateResponse("session.html", ctx)


# ---------------------------------------------------------------------------
# Routes — pipeline partial (refreshed after each task)
# ---------------------------------------------------------------------------

@app.get("/session/{sid}/pipeline", response_class=HTMLResponse)
async def pipeline_partial(request: Request, sid: str):
    ctx = _session_ctx(sid)
    ctx["request"] = request
    return templates.TemplateResponse("partials/pipeline.html", ctx)


# ---------------------------------------------------------------------------
# Routes — start tasks
# ---------------------------------------------------------------------------

@app.post("/session/{sid}/run/questions", response_class=HTMLResponse)
async def run_questions(request: Request, sid: str):
    task_id = uuid.uuid4().hex[:8]

    def _work():
        from agents.strategy_agent import StrategyAgent
        s = _session(sid)
        cv = _cv_path(sid).read_text("utf-8")
        agent = StrategyAgent(Settings.load(), s)
        qs = agent.generate_questions(cv)
        s.write_json("strategy/coaching_questions.json", qs)
        return {"questions": qs}

    _start(task_id, _work)
    return templates.TemplateResponse("partials/task_running.html", {
        "request": request, "task_id": task_id, "sid": sid,
        "message": "Анализирую CV, формулирую вопросы…",
    })


@app.post("/session/{sid}/intake", response_class=HTMLResponse)
async def submit_intake(request: Request, sid: str, answers_json: str = Form("")):
    """User submitted coaching answers → run full strategy."""
    task_id = uuid.uuid4().hex[:8]
    answers = json.loads(answers_json) if answers_json.strip() else {}

    def _work():
        s = _session(sid)
        intake_path = s.write_json("strategy/intake_answers.json", answers)
        orc = Orchestrator(session=s, cv_path=str(_cv_path(sid)))
        return orc.strategy(intake_path=str(intake_path))

    _start(task_id, _work)
    return templates.TemplateResponse("partials/task_running.html", {
        "request": request, "task_id": task_id, "sid": sid,
        "message": "Провожу веб-ресёрч и пишу стратегию (~5 мин)…",
    })


@app.post("/session/{sid}/run/{agent}", response_class=HTMLResponse)
async def run_agent(request: Request, sid: str, agent: str,
                    job_id: str = Form("")):
    task_id = uuid.uuid4().hex[:8]
    labels = {
        "base-cv":    "Переписываю CV под стратегическое позиционирование…",
        "linkedin":   "Создаю LinkedIn-профиль…",
        "hunt":       "Сканирую каналы вакансий (~5–10 мин)…",
        "bulk-resume":"Пакетная адаптация Tier B…",
        "content":    "Пишу контент-план и посты…",
        "interview":  "Готовлю пакет к интервью…",
        "resume":     f"Адаптирую резюме под вакансию {job_id}…",
        "outreach":   f"Готовлю outreach для вакансии {job_id}…",
    }

    def _work():
        s = _session(sid)
        orc = Orchestrator(session=s, cv_path=str(_cv_path(sid)))
        dispatch = {
            "base-cv":    orc.base_cv,
            "linkedin":   orc.linkedin,
            "hunt":       orc.hunt,
            "bulk-resume": lambda: orc.bulk_resume("B"),
            "content":    orc.content,
            "interview":  lambda: orc.interview(job_id or None),
            "resume":     lambda: orc.resume(job_id),
            "outreach":   lambda: orc.outreach(job_id),
        }
        return dispatch[agent]()

    _start(task_id, _work)
    return templates.TemplateResponse("partials/task_running.html", {
        "request": request, "task_id": task_id, "sid": sid,
        "message": labels.get(agent, "Запускаю…"),
    })


# ---------------------------------------------------------------------------
# Routes — task polling
# ---------------------------------------------------------------------------

@app.get("/session/{sid}/task/{task_id}", response_class=HTMLResponse)
async def task_status(request: Request, sid: str, task_id: str):
    task = _get_task(task_id)
    status = task["status"]

    if status == "running":
        return templates.TemplateResponse("partials/task_running.html", {
            "request": request, "task_id": task_id, "sid": sid,
            "message": "Выполняется…",
        })

    if status == "error":
        return templates.TemplateResponse("partials/task_error.html", {
            "request": request, "sid": sid,
            "error": task.get("error", "Неизвестная ошибка"),
        })

    # Done — check if strategy returned questions
    result = task.get("result", {})
    if result.get("stage") == "awaiting_intake":
        ctx = _session_ctx(sid)
        ctx["request"] = request
        return templates.TemplateResponse("partials/questions.html", ctx)

    return templates.TemplateResponse("partials/task_done.html", {
        "request": request, "sid": sid, "result": result,
    })


# ---------------------------------------------------------------------------
# Routes — files
# ---------------------------------------------------------------------------

@app.get("/session/{sid}/vacancies", response_class=HTMLResponse)
async def vacancies_page(request: Request, sid: str):
    s = _session(sid)
    p = s.recall("vacancies_html")
    if p and Path(p).exists():
        return HTMLResponse(Path(p).read_text("utf-8"))
    return HTMLResponse("<p style='color:white;padding:2rem'>Запустите hunt сначала.</p>", 404)


@app.get("/session/{sid}/file/{fp:path}")
async def download_file(sid: str, fp: str):
    path = OUTPUT_DIR / sid / fp
    if path.is_file():
        return FileResponse(str(path), filename=path.name)
    return HTMLResponse("Файл не найден", 404)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
