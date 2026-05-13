from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Session:
    """Один сеанс работы консультанта: общая папка для всех артефактов агентов."""

    root: Path
    session_id: str
    state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def open(cls, session_id: str | None = None, base_dir: Path | str = "output") -> "Session":
        sid = session_id or time.strftime("%Y%m%d-%H%M%S")
        root = Path(base_dir) / sid
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / "state.json"
        state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else {}
        return cls(root=root, session_id=sid, state=state)

    # ----- artefact helpers -----

    def write_text(self, name: str, content: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, name: str, data: Any) -> Path:
        return self.write_text(name, json.dumps(data, ensure_ascii=False, indent=2))

    def read_text(self, name: str) -> str | None:
        path = self.root / name
        return path.read_text("utf-8") if path.exists() else None

    def read_json(self, name: str) -> Any:
        text = self.read_text(name)
        return json.loads(text) if text else None

    def remember(self, key: str, value: Any) -> None:
        self.state[key] = value
        self.write_json("state.json", self.state)

    def recall(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)
