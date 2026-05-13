from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from tools.job_channels.base import Job


class CryptoJobsListChannel:
    """cryptojobslist.com — публичный листинг."""

    name = "crypto_jobs"
    BASE = "https://cryptojobslist.com"

    def search(self, queries: list[str], *, limit: int) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True) as cli:
            for q in queries:
                try:
                    r = cli.get(f"{self.BASE}/engineering", params={"query": q})
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")
                except Exception:
                    continue

                for a in soup.select('a[href^="/jobs/"]')[: limit * 2]:
                    href = a.get("href", "")
                    if not href.startswith("/jobs/"):
                        continue
                    parent = a.find_parent()
                    title = a.get_text(" ", strip=True)
                    if not title or len(title) < 4:
                        continue
                    snippet = parent.get_text(" ", strip=True)[:400] if parent else ""
                    jobs.append(Job(
                        title=title,
                        company=_first_segment(snippet),
                        location="Remote / Crypto",
                        url=f"{self.BASE}{href}",
                        snippet=snippet,
                        source="cryptojobslist",
                    ))
                    if len(jobs) >= limit:
                        break
        return _dedup(jobs)[:limit]


def _first_segment(s: str) -> str:
    parts = [p for p in (s or "").split("·") if p.strip()]
    return parts[0].strip() if parts else ""


def _dedup(jobs: list[Job]) -> list[Job]:
    seen, out = set(), []
    for j in jobs:
        if j.id in seen:
            continue
        seen.add(j.id)
        out.append(j)
    return out
