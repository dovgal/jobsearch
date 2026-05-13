from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from tools.job_channels.base import Job

JOB_HINTS = re.compile(r"(vacancy|вакансия|hiring|ищем|looking for|opening|роль|роли)", re.I)


class TelegramChannel:
    """Telegram-каналы: тянем последние посты через t.me/s/<channel>.

    Без авторизации, только публичные каналы.
    """

    name = "telegram"

    def __init__(self, channels: list[str]):
        self.channels = [self._normalize(c) for c in channels]

    @staticmethod
    def _normalize(c: str) -> str:
        c = c.strip().lstrip("@")
        if c.startswith("https://t.me/"):
            c = c.split("/")[-1]
        return c

    def search(self, queries: list[str], *, limit: int) -> list[Job]:
        jobs: list[Job] = []
        if not self.channels:
            return jobs
        with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True) as cli:
            for ch in self.channels:
                try:
                    r = cli.get(f"https://t.me/s/{ch}")
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")
                except Exception:
                    continue
                posts = soup.select(".tgme_widget_message")[-200:]
                for p in posts:
                    text_div = p.select_one(".tgme_widget_message_text")
                    if not text_div:
                        continue
                    text = text_div.get_text("\n", strip=True)
                    if not JOB_HINTS.search(text) and not any(q.lower() in text.lower() for q in queries):
                        continue
                    if queries and not any(q.lower() in text.lower() for q in queries):
                        continue
                    link_a = p.select_one(".tgme_widget_message_date") or p.select_one('a[href*="t.me/"]')
                    link = link_a.get("href") if link_a else f"https://t.me/{ch}"
                    first_line = text.splitlines()[0][:120]
                    jobs.append(Job(
                        title=first_line,
                        company=ch,
                        location="—",
                        url=link or f"https://t.me/{ch}",
                        snippet=text[:600],
                        source=f"tg:{ch}",
                    ))
                    if len(jobs) >= limit:
                        break
                if len(jobs) >= limit:
                    break
        return jobs[:limit]
