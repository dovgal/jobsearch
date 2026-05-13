from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from tools.job_channels.base import Job


class Web3CareerChannel:
    """web3.career — публичный листинг, без API. Скрейпим HTML."""

    name = "web3_career"
    BASE = "https://web3.career"

    def search(self, queries: list[str], *, limit: int) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}) as cli:
            for q in queries:
                try:
                    r = cli.get(self.BASE, params={"search": q})
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")
                except Exception:
                    continue

                for tr in soup.select("table tbody tr")[: limit]:
                    title_a = tr.select_one('a[href*="/jobs/"]') or tr.select_one("a")
                    if not title_a:
                        continue
                    href = title_a.get("href", "")
                    if href.startswith("/"):
                        href = f"{self.BASE}{href}"
                    company_td = tr.select_one("td:nth-of-type(2)") or tr.select_one(".job-company")
                    loc_td = tr.select_one(".location") or tr.select_one("td:nth-of-type(3)")
                    salary_td = tr.select_one(".salary")
                    tags = [t.get_text(strip=True) for t in tr.select(".tag, .skills a")][:6]
                    jobs.append(Job(
                        title=title_a.get_text(strip=True),
                        company=company_td.get_text(strip=True) if company_td else "",
                        location=loc_td.get_text(strip=True) if loc_td else "Remote",
                        url=href,
                        snippet=tr.get_text(" ", strip=True)[:400],
                        source="web3.career",
                        salary=salary_td.get_text(strip=True) if salary_td else None,
                        tags=tags,
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
