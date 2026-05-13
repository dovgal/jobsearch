from __future__ import annotations

import json
import re
from pathlib import Path


def read_text_file(path: Path | str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_text("utf-8", errors="ignore")


def extract_json_block(text: str) -> dict | list | None:
    """Вытащить первый сбалансированный JSON-блок из ответа LLM.

    Модели любят оборачивать JSON в ```json … ``` или добавлять прозу до/после.
    """
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else None
    if not candidate:
        # ищем первый '{' или '[' и пытаемся пройти скобки
        start = None
        for i, ch in enumerate(text):
            if ch in "{[":
                start = i
                break
        if start is None:
            return None
        depth = 0
        in_str = False
        esc = False
        for j in range(start, len(text)):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
                continue
            if ch in "{[":
                depth += 1
            elif ch in "}]":
                depth -= 1
                if depth == 0:
                    candidate = text[start:j + 1]
                    break
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
