from __future__ import annotations

from dataclasses import dataclass

import httpx

from core.settings import env


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # "brave" | "tavily" | "serper"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
        }


class WebSearch:
    """Web-поиск с fallback по нескольким провайдерам.

    Порядок попыток задаётся в config.yaml → web_search.providers.
    """

    def __init__(self, providers: list[str], results_per_query: int = 8):
        self.providers = providers
        self.results_per_query = results_per_query

    # ------------ public ------------

    def search(self, query: str) -> list[SearchResult]:
        for p in self.providers:
            try:
                if p == "brave":
                    return self._brave(query)
                if p == "tavily":
                    return self._tavily(query)
                if p == "serper":
                    return self._serper(query)
            except Exception:
                continue
        return []

    # ------------ implementations ------------

    def _brave(self, query: str) -> list[SearchResult]:
        key = env("BRAVE_SEARCH_API_KEY")
        if not key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY empty")
        with httpx.Client(timeout=20.0) as cli:
            r = cli.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": self.results_per_query},
                headers={"Accept": "application/json", "X-Subscription-Token": key},
            )
            r.raise_for_status()
            data = r.json()
        out: list[SearchResult] = []
        for w in (data.get("web") or {}).get("results") or []:
            out.append(SearchResult(
                title=w.get("title", ""),
                url=w.get("url", ""),
                snippet=w.get("description", ""),
                source="brave",
            ))
        return out

    def _tavily(self, query: str) -> list[SearchResult]:
        key = env("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY empty")
        with httpx.Client(timeout=30.0) as cli:
            r = cli.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": query,
                    "max_results": self.results_per_query,
                    "include_answer": False,
                },
            )
            r.raise_for_status()
            data = r.json()
        out: list[SearchResult] = []
        for w in data.get("results") or []:
            out.append(SearchResult(
                title=w.get("title", ""),
                url=w.get("url", ""),
                snippet=w.get("content", "")[:400],
                source="tavily",
            ))
        return out

    def _serper(self, query: str) -> list[SearchResult]:
        key = env("SERPER_API_KEY")
        if not key:
            raise RuntimeError("SERPER_API_KEY empty")
        with httpx.Client(timeout=20.0) as cli:
            r = cli.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "num": self.results_per_query},
            )
            r.raise_for_status()
            data = r.json()
        out: list[SearchResult] = []
        for w in data.get("organic") or []:
            out.append(SearchResult(
                title=w.get("title", ""),
                url=w.get("link", ""),
                snippet=w.get("snippet", ""),
                source="serper",
            ))
        return out
