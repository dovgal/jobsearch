from __future__ import annotations

from typing import Iterable

from llm.base import LLMResponse, Message
from llm.providers._http import post_json


class GoogleClient:
    """Google Generative Language API (Gemini)."""

    provider = "google"

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
        msgs = list(messages)
        system_parts = [m.content for m in msgs if m.role == "system"]
        contents = []
        for m in msgs:
            if m.role == "system":
                continue
            contents.append(
                {
                    "role": "user" if m.role == "user" else "model",
                    "parts": [{"text": m.content}],
                }
            )

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        if stop:
            body["generationConfig"]["stopSequences"] = stop

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        data = post_json(url, headers={"Content-Type": "application/json"}, json=body)

        text = ""
        cands = data.get("candidates") or []
        if cands:
            for part in (cands[0].get("content") or {}).get("parts", []):
                text += part.get("text", "")
        usage = {
            "prompt_tokens": (data.get("usageMetadata") or {}).get("promptTokenCount"),
            "completion_tokens": (data.get("usageMetadata") or {}).get("candidatesTokenCount"),
        }
        return LLMResponse(text=text, model=self.model, provider=self.provider, usage=usage, raw=data)
