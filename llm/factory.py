from __future__ import annotations

import os
from typing import Any

from llm.base import LLMClient
from llm.providers.anthropic import AnthropicClient
from llm.providers.google import GoogleClient
from llm.providers.ollama import OllamaClient
from llm.providers.openai_compat import OpenAICompatClient


def _env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Environment variable {name} is empty. "
            "Положите ключ в .env или экспортируйте в шелл."
        )
    return val


def build_client(provider: str, config: dict[str, Any], *, agent_overrides: dict | None = None) -> LLMClient:
    """Собрать клиента для нужного провайдера.

    `config` — секция `providers.<name>` из YAML.
    `agent_overrides` — секция `agents.<name>` (используется только для `model`).
    """
    overrides = agent_overrides or {}
    model = overrides.get("model") or config.get("model")
    base_url = config.get("base_url")
    api_key = _env(config["api_key_env"]) if config.get("api_key_env") else ""

    if provider == "ollama":
        return OllamaClient(base_url=base_url, api_key=api_key, model=model)

    if provider == "anthropic":
        return AnthropicClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            anthropic_version=config.get("anthropic_version", "2023-06-01"),
        )

    if provider == "google":
        return GoogleClient(base_url=base_url, api_key=api_key, model=model)

    # Все остальные провайдеры из ТЗ (xAI Grok, DeepSeek, Qwen/DashScope,
    # OpenRouter) — OpenAI-совместимые. Один клиент с разными URL/моделями.
    if provider in {"xai", "deepseek", "qwen", "openrouter", "openai"}:
        return OpenAICompatClient(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")
