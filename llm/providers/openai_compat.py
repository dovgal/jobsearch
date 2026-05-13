from __future__ import annotations

from typing import Iterable

from llm.base import LLMResponse, Message
from llm.providers._http import post_json


class OpenAICompatClient:
    """Универсальный клиент для OpenAI-совместимых endpoint-ов.

    Используется для xAI (Grok), DeepSeek, Qwen/DashScope, OpenRouter
    и любого другого API, повторяющего схему /chat/completions.
    """

    def __init__(self, provider: str, base_url: str, api_key: str, model: str):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: Iterable[Message],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            body["stop"] = stop

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # OpenRouter рекомендует HTTP-Referer и X-Title
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/dovgal/jobsearch"
            headers["X-Title"] = "job-search-consultation"

        data = post_json(f"{self.base_url}/chat/completions", headers=headers, json=body)
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "") or ""
        usage = {
            "prompt_tokens": (data.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (data.get("usage") or {}).get("completion_tokens"),
        }
        return LLMResponse(text=text, model=self.model, provider=self.provider, usage=usage, raw=data)
