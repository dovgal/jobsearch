from __future__ import annotations

from agents.base import Agent


class LinkedInAgent(Agent):
    """💼 Полный LinkedIn-профиль."""

    name = "linkedin"

    def run(self, cv_md: str, strategy_md: str) -> dict:
        prompt = (
            "Создай полный LinkedIn-профиль в соответствии со стратегией и базовым CV.\n"
            "Headline ≤ 220 знаков, About с hook в первых 250 знаках.\n"
            "Возврат — markdown по жёсткой структуре из системного промпта.\n\n"
            f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n\n"
            f"=== Base CV ===\n{cv_md}\n=== /Base CV ===\n"
        )
        linkedin_md = self.ask(prompt, max_tokens=self.max_tokens)

        headline_len = _headline_length(linkedin_md)
        if headline_len > 220:
            tighten = (
                "Headline получился длиннее 220 знаков "
                f"(сейчас {headline_len}). Сократи только секцию `## Headline`, "
                "сохрани ключевики. Верни ВЕСЬ профиль целиком."
            )
            linkedin_md = self.ask(tighten + "\n\n" + linkedin_md, max_tokens=self.max_tokens)
            headline_len = _headline_length(linkedin_md)

        path = self.session.write_text("linkedin/profile.md", linkedin_md)
        self.session.remember("linkedin_path", str(path))
        return {"linkedin_path": str(path), "headline_length": headline_len}


def _headline_length(md: str) -> int:
    lines = md.splitlines()
    for i, l in enumerate(lines):
        if l.strip().lower().startswith("## headline"):
            for j in range(i + 1, len(lines)):
                t = lines[j].strip()
                if t and not t.startswith("#"):
                    return len(t)
            break
    return 0
