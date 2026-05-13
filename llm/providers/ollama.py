from __future__ import annotations

from typing import Iterable

from llm.base import LLMResponse, Message
from llm.providers._http import post_json


class OllamaClient:
    """Клиент Ollama (cloud Turbo и локальный — один протокол).

    Cloud endpoint: https://ollama.com  (требует Bearer-токен).
    Local endpoint: http://localhost:11434 (без авторизации).
    """

    provider = "ollama"

    def __init__(self, base_url: str, api_key: str, model: str):
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
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if stop:
            body["options"]["stop"] = stop

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = post_json(f"{self.base_url}/api/chat", headers=headers, json=body)
        text = (data.get("message") or {}).get("content", "")
        usage = {
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
        }
        return LLMResponse(text=text, model=self.model, provider=self.provider, usage=usage, raw=data)
