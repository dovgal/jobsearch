from __future__ import annotations

from tools.job_channels.base import Job
from tools.web_search import WebSearch


class LinkedInChannel:
    """LinkedIn — без официального API.

    Используем Google/Brave-индекс публичных страниц /jobs/view/.
    """

    name = "linkedin"

    def __init__(self, web_search: WebSearch):
        self.web = web_search

    def search(self, queries: list[str], *, limit: int) -> list[Job]:
        jobs: list[Job] = []
        for q in queries:
            results = self.web.search(f'site:linkedin.com/jobs/view "{q}"')
            for r in results[:limit]:
                jobs.append(Job(
                    title=r.title.split(" | ")[0].strip(),
                    company=_company_from_snippet(r.snippet),
                    location=_location_from_snippet(r.snippet),
                    url=r.url,
                    snippet=r.snippet,
                    source="linkedin",
                ))
        return _dedup(jobs)[:limit]


def _company_from_snippet(s: str) -> str:
    parts = [p.strip() for p in (s or "").split("·")]
    return parts[0] if parts else ""


def _location_from_snippet(s: str) -> str:
    parts = [p.strip() for p in (s or "").split("·")]
    return parts[1] if len(parts) > 1 else ""


def _dedup(jobs: list[Job]) -> list[Job]:
    seen, out = set(), []
    for j in jobs:
        if j.id in seen:
            continue
        seen.add(j.id)
        out.append(j)
    return out
