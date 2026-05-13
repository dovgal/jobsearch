from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9\+\#\.\-]{2,}")
STOP = {
    "and", "or", "the", "a", "an", "of", "to", "for", "with", "in", "on",
    "is", "are", "be", "as", "by", "at", "from", "this", "that", "we", "you",
    "your", "our", "their", "и", "или", "в", "на", "по", "из", "не", "что",
    "это", "для", "как", "так", "же", "то", "также", "the", "etc", "more",
}


def _tokens(text: str) -> list[str]:
    return [
        t.lower() for t in WORD_RE.findall(text or "")
        if t.lower() not in STOP and not t.isdigit()
    ]


@dataclass
class ATSReport:
    score: float                        # 0..1
    matched_keywords: list[str]
    missing_keywords: list[str]
    density: dict[str, int]             # сколько раз ключевик встречается в резюме

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "density": self.density,
        }


def extract_keywords(job_description: str, top_n: int = 40) -> list[str]:
    """Грубый, но рабочий extractor: TF на n-grams 1..2 от JD без стоп-слов."""
    text = job_description or ""
    unigrams = _tokens(text)
    bigrams = [f"{a} {b}" for a, b in zip(unigrams, unigrams[1:])]
    counts = Counter(unigrams) + Counter(bigrams)
    # биграммы умножаем — они информативнее
    boosted = Counter({k: v * (2 if " " in k else 1) for k, v in counts.items()})
    return [w for w, _ in boosted.most_common(top_n)]


def score_resume(resume_text: str, job_description: str) -> ATSReport:
    """Сколько ATS-ключевиков из JD реально встречается в резюме."""
    keywords = extract_keywords(job_description)
    if not keywords:
        return ATSReport(score=0.0, matched_keywords=[], missing_keywords=[], density={})

    rl = (resume_text or "").lower()
    matched: list[str] = []
    missing: list[str] = []
    density: dict[str, int] = {}
    for kw in keywords:
        n = rl.count(kw)
        density[kw] = n
        (matched if n > 0 else missing).append(kw)

    score = len(matched) / len(keywords)
    return ATSReport(
        score=score,
        matched_keywords=matched,
        missing_keywords=missing,
        density=density,
    )
