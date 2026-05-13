from __future__ import annotations

import html
import json
from pathlib import Path


def render_vacancies_html(vacancies: list[dict], out_path: Path, *, title: str = "Vacancy review") -> Path:
    """Интерактивный HTML с карточками: Apply / Skip / Need-info свайпом с телефона.

    Решения сохраняются в LocalStorage и экспортируются JSON-ом по кнопке.
    """
    data_json = json.dumps(vacancies, ensure_ascii=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_TEMPLATE.replace("__DATA__", data_json).replace("__TITLE__", html.escape(title)), "utf-8")
    return out_path


_TEMPLATE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>__TITLE__</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0;
    font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0d0f12; color: #e8eaed;
    overscroll-behavior-y: contain;
  }
  header {
    position: sticky; top: 0; z-index: 5;
    padding: 14px 16px; background: #11141a; border-bottom: 1px solid #20242c;
    display: flex; justify-content: space-between; align-items: center;
  }
  header h1 { margin: 0; font-size: 16px; font-weight: 600; }
  header .stats { font-size: 12px; color: #9aa0a6; }
  main { padding: 16px; padding-bottom: 120px; }
  .card {
    background: #161a22; border: 1px solid #20242c; border-radius: 14px;
    padding: 16px; margin-bottom: 14px;
    touch-action: pan-y;
  }
  .card.done { opacity: 0.35; }
  .row { display: flex; justify-content: space-between; gap: 10px; }
  .title { font-size: 17px; font-weight: 600; margin: 0 0 4px; }
  .company { color: #c7cdd6; }
  .meta { font-size: 12px; color: #9aa0a6; margin-top: 6px; }
  .tags { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    background: #1f2530; border: 1px solid #2a3140;
    border-radius: 999px; padding: 3px 9px; font-size: 11px; color: #b8c1cf;
  }
  .score { font-weight: 700; font-size: 13px; }
  .score.hi { color: #4ade80; }
  .score.md { color: #facc15; }
  .score.lo { color: #f87171; }
  details { margin-top: 10px; }
  summary { color: #8ab4f8; cursor: pointer; outline: none; }
  .reasons { font-size: 13px; color: #c7cdd6; padding-left: 18px; margin: 8px 0; }
  .actions {
    position: fixed; bottom: 16px; left: 16px; right: 16px; z-index: 6;
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;
  }
  .actions button {
    padding: 14px 0; font-size: 15px; font-weight: 600; border: 0; border-radius: 12px;
    color: #0d0f12;
  }
  .btn-skip  { background: #f87171; }
  .btn-info  { background: #facc15; }
  .btn-apply { background: #4ade80; }
  .export {
    position: fixed; top: 14px; right: 16px; z-index: 7;
    background: transparent; color: #8ab4f8; border: 1px solid #2a3140;
    border-radius: 8px; padding: 6px 10px; font-size: 12px;
  }
  .decision-label {
    display: inline-block; margin-top: 8px; padding: 2px 8px;
    border-radius: 6px; font-size: 11px; font-weight: 600;
  }
  .decision-apply { background: #14532d; color: #4ade80; }
  .decision-skip  { background: #5b1a1a; color: #f87171; }
  .decision-info  { background: #5a4a0a; color: #facc15; }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="stats" id="stats"></div>
</header>
<button class="export" onclick="exportDecisions()">Export ⤓</button>
<main id="list"></main>
<div class="actions">
  <button class="btn-skip"  onclick="decide('skip')">Skip</button>
  <button class="btn-info"  onclick="decide('info')">Need info</button>
  <button class="btn-apply" onclick="decide('apply')">Apply</button>
</div>

<script>
  const VACANCIES = __DATA__;
  const STORAGE_KEY = "vacancy_decisions_v1";
  const decisions = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  let current = 0;

  function scoreClass(s) { return s >= 0.75 ? "hi" : s >= 0.55 ? "md" : "lo"; }

  function render() {
    const list = document.getElementById("list");
    list.innerHTML = "";
    VACANCIES.forEach((v, idx) => {
      const div = document.createElement("div");
      div.className = "card" + (decisions[v.id] ? " done" : "");
      div.id = "card-" + idx;
      const reasons = (v.score_reasons || []).map(r => `<li>${r}</li>`).join("");
      const tags = (v.tags || []).map(t => `<span class="tag">${t}</span>`).join("");
      const decLabel = decisions[v.id]
        ? `<div class="decision-label decision-${decisions[v.id]}">${decisions[v.id].toUpperCase()}</div>`
        : "";
      div.innerHTML = `
        <div class="row">
          <div>
            <h3 class="title">${v.title || ""}</h3>
            <div class="company">${v.company || ""}</div>
            <div class="meta">${v.location || ""} · ${v.salary || "—"} · ${v.source || ""}</div>
          </div>
          <div class="score ${scoreClass(v.score || 0)}">${Math.round((v.score || 0) * 100)}</div>
        </div>
        <div class="tags">${tags}</div>
        ${reasons ? `<details><summary>Why this match</summary><ul class="reasons">${reasons}</ul></details>` : ""}
        <details><summary>JD excerpt</summary><div class="reasons">${(v.snippet || "").replace(/</g, "&lt;")}</div></details>
        <div><a href="${v.url || "#"}" target="_blank" rel="noopener" style="color:#8ab4f8; font-size:13px;">Open job posting →</a></div>
        ${decLabel}
      `;
      list.appendChild(div);
    });
    updateStats();
  }

  function decide(kind) {
    if (current >= VACANCIES.length) return;
    const v = VACANCIES[current];
    decisions[v.id] = kind;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
    current = Math.min(current + 1, VACANCIES.length);
    render();
    const next = document.getElementById("card-" + current);
    if (next) next.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function updateStats() {
    const counts = { apply: 0, skip: 0, info: 0 };
    Object.values(decisions).forEach(k => { counts[k] = (counts[k] || 0) + 1; });
    document.getElementById("stats").textContent =
      `${counts.apply}✓ · ${counts.info}? · ${counts.skip}✗ / ${VACANCIES.length}`;
  }

  function exportDecisions() {
    const payload = VACANCIES.map(v => ({ id: v.id, decision: decisions[v.id] || null, url: v.url, title: v.title, company: v.company }));
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "decisions.json";
    a.click();
  }

  for (let i = 0; i < VACANCIES.length; i++) {
    if (!decisions[VACANCIES[i].id]) { current = i; break; }
    current = i + 1;
  }
  render();
</script>
</body>
</html>
"""
