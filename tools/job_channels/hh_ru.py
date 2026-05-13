from __future__ import annotations

import httpx

from tools.job_channels.base import Job


class HHRuChannel:
    """hh.ru — открытый JSON API, ключ не требуется."""

    name = "hh_ru"
    BASE = "https://api.hh.ru/vacancies"

    def search(self, queries: list[str], *, limit: int) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=30.0, headers={"User-Agent": "job-search-consultation/1.0"}) as cli:
            for q in queries:
                try:
                    r = cli.get(self.BASE, params={"text": q, "per_page": min(limit, 50), "order_by": "publication_time"})
                    r.raise_for_status()
                    data = r.json()
                except Exception:
                    continue
                for item in data.get("items") or []:
                    salary = item.get("salary") or {}
                    salary_str = None
                    if salary:
                        lo, hi, cur = salary.get("from"), salary.get("to"), salary.get("currency")
                        if lo or hi:
                            salary_str = f"{lo or '?'}–{hi or '?'} {cur or ''}".strip()
                    jobs.append(Job(
                        title=item.get("name", ""),
                        company=(item.get("employer") or {}).get("name", ""),
                        location=(item.get("area") or {}).get("name", ""),
                        url=item.get("alternate_url", ""),
                        snippet=(item.get("snippet") or {}).get("responsibility", "") or "",
                        source="hh.ru",
                        salary=salary_str,
                        posted_at=item.get("published_at"),
                    ))
        return _dedup(jobs)[:limit]


def _dedup(jobs: list[Job]) -> list[Job]:
    seen, out = set(), []
    for j in jobs:
        if j.id in seen:
            continue
        seen.add(j.id)
        out.append(j)
    return out
