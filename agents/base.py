from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.session import Session
from core.settings import Settings
from llm import LLMClient, Message, build_client

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class Agent:
    """Базовый класс агента: знает свою конфигурацию, LLM и сессию."""

    name: str = ""

    def __init__(self, settings: Settings, session: Session):
        self.settings = settings
        self.session = session

        provider, p_cfg, a_cfg = settings.resolve_agent(self.name)
        self.provider_name = provider
        self.provider_cfg = p_cfg
        self.agent_cfg = a_cfg

        self.llm: LLMClient = build_client(provider, p_cfg, agent_overrides=a_cfg)
        self.temperature: float = float(a_cfg.get("temperature", settings.default_temperature()))
        self.max_tokens: int = int(a_cfg.get("max_tokens", settings.default_max_tokens()))

    # ----- LLM helpers -----

    def system_prompt(self) -> str:
        parts: list[str] = []
        market_ctx = PROMPTS_DIR / "market-context.md"
        if market_ctx.exists():
            parts.append(market_ctx.read_text("utf-8"))
        path = PROMPTS_DIR / f"{self.name}.md"
        if path.exists():
            parts.append(path.read_text("utf-8"))
        return "\n\n---\n\n".join(parts)

    def ask(
        self,
        user_prompt: str,
        *,
        extra_messages: Iterable[Message] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        messages: list[Message] = []
        sp = self.system_prompt()
        if sp:
            messages.append(Message(role="system", content=sp))
        if extra_messages:
            messages.extend(extra_messages)
        messages.append(Message(role="user", content=user_prompt))
        resp = self.llm.complete(
            messages,
            temperature=self.temperature if temperature is None else temperature,
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
        )
        return resp.text.strip()
