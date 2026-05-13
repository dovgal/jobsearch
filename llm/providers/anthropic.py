from __future__ import annotations

from typing import Iterable

from llm.base import LLMResponse, Message
from llm.providers._http import post_json


class AnthropicClient:
    """Anthropic /v1/messages."""

    provider = "anthropic"

    def __init__(self, base_url: str, api_key: str, model: str, anthropic_version: str = "2023-06-01"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.anthropic_version = anthropic_version

    def complete(
        self,
        messages: Iterable[Message],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        msgs = list(messages)
        # У Anthropic system — отдельное поле верхнего уровня.
        system_parts = [m.content for m in msgs if m.role == "system"]
        conv = [{"role": m.role, "content": m.content} for m in msgs if m.role != "system"]
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)
        if stop:
            body["stop_sequences"] = stop

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
        }
        data = post_json(f"{self.base_url}/v1/messages", headers=headers, json=body)
        text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
        usage = {
            "prompt_tokens": (data.get("usage") or {}).get("input_tokens"),
            "completion_tokens": (data.get("usage") or {}).get("output_tokens"),
        }
        return LLMResponse(text=text, model=self.model, provider=self.provider, usage=usage, raw=data)
