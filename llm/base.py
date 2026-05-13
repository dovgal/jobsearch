from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    raw: dict | None = None


class LLMClient(Protocol):
    """Минимальный интерфейс для любого провайдера.

    Конкретные реализации сами знают, как перевести список Message в нужный
    формат API (Anthropic /messages, OpenAI /chat/completions, Gemini
    /generateContent и т.д.).
    """

    provider: str
    model: str

    def complete(
        self,
        messages: Iterable[Message],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> LLMResponse: ...
