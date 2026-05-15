from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


@dataclass
class Settings:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Settings":
        load_dotenv(override=True)  # подхватываем .env, если есть; override=True чтобы обновлять ключи без перезапуска
        with open(path or CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(raw=data)

    # ----- helpers -----

    def default_provider(self) -> str:
        return self.raw.get("default_provider", "ollama")

    def default_temperature(self) -> float:
        return float(self.raw.get("default_temperature", 0.4))

    def default_max_tokens(self) -> int:
        return int(self.raw.get("default_max_tokens", 4096))

    def provider_config(self, provider: str) -> dict[str, Any]:
        return (self.raw.get("providers") or {}).get(provider) or {}

    def agent_config(self, agent: str) -> dict[str, Any]:
        return (self.raw.get("agents") or {}).get(agent) or {}

    def resolve_agent(self, agent: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Вернуть (provider_name, provider_cfg, agent_cfg)."""
        a_cfg = self.agent_config(agent)
        provider = a_cfg.get("provider") or self.default_provider()
        p_cfg = self.provider_config(provider)
        if not p_cfg:
            raise RuntimeError(f"Provider '{provider}' is not configured in config.yaml")
        return provider, p_cfg, a_cfg

    def web_search_cfg(self) -> dict[str, Any]:
        return self.raw.get("web_search") or {}

    def job_channels(self) -> dict[str, Any]:
        return self.raw.get("job_channels") or {}


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()
