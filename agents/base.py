from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.session import Session
from core.settings import Settings
from llm import LLMClient, Message, build_client

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

LANG_INSTRUCTIONS: dict[str, str] = {
    "fr": """## LANGUE DE SORTIE OBLIGATOIRE : Français

Tous les documents que tu génères (CV, stratégie, lettre de motivation, profil LinkedIn,
messages d'outreach, posts, questions de coaching, préparation à l'entretien) doivent être
rédigés intégralement en **français**, avec un niveau de langue professionnel et naturel.

- Le CV fourni en entrée peut être dans une autre langue — traduis-le et adapte-le en français.
- Les titres de section, les bullet points, les formules de politesse : tout en français.
- Utilise le vocabulaire RH français : "poste", "candidature", "entretien", "lettre de motivation", "CV", etc.
- Évite les anglicismes superflus sauf quand ils sont d'usage courant en France (ex. "CEO", "Data Engineer").""",

    "en": """## OUTPUT LANGUAGE: English

All documents you generate (CV/resume, strategy, cover letter, LinkedIn profile,
outreach messages, posts, coaching questions, interview prep) must be written entirely
in **English**, at a professional and natural level.

- The input CV may be in another language — translate and adapt it fully into English.
- Section headings, bullet points, salutations: everything in English.
- Use standard professional HR vocabulary: "position", "application", "interview", "cover letter", "resume", etc.
- Adapt terminology to the target market (UK/US/international English as appropriate).""",

    "ru": """## ЯЗЫК ВЫВОДА: Русский

Все генерируемые документы (резюме, стратегия, сопроводительное письмо, LinkedIn-профиль,
outreach-сообщения, посты, вопросы коучинга, подготовка к интервью) должны быть написаны
полностью на **русском языке**, профессионально и естественно.

- Входное резюме может быть на другом языке — переведи и адаптируй полностью.
- Заголовки секций, пункты списков, формулы обращения — всё на русском.
- Используй стандартную HR-терминологию: "должность", "кандидатура", "собеседование", "резюме" и т.д.""",
}


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

        # 1. Язык вывода (высший приоритет — первый в промпте)
        lang = self.session.recall("language", "fr")
        if lang in LANG_INSTRUCTIONS:
            parts.append(LANG_INSTRUCTIONS[lang])

        # 2. Контекст рынка
        market_ctx = PROMPTS_DIR / "market-context.md"
        if market_ctx.exists():
            parts.append(market_ctx.read_text("utf-8"))

        # 3. Инструкция агента
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
