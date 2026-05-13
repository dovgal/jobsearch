from __future__ import annotations

from agents.base import Agent


class ContentAgent(Agent):
    """📝 LinkedIn-контент-план + 4 готовых поста в tone of voice клиента."""

    name = "content"

    def run(self, cv_md: str, strategy_md: str, voice_samples: str = "") -> dict:
        prompt = (
            "Сформируй 4-недельный контент-план и напиши 4 готовых поста для LinkedIn.\n"
            "Tone-of-voice вычисляй из voice_samples (если переданы), иначе из CV.\n\n"
            f"=== Strategy ===\n{strategy_md}\n=== /Strategy ===\n\n"
            f"=== CV ===\n{cv_md}\n=== /CV ===\n\n"
            f"=== Voice samples ===\n{voice_samples or '(нет — выведи стиль из CV)'}\n=== /Voice samples ===\n"
        )
        out = self.ask(prompt, max_tokens=self.max_tokens)
        path = self.session.write_text("content/posts.md", out)
        return {"content_path": str(path)}
