from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    snippet: str
    source: str
    salary: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            digest = hashlib.sha1(f"{self.source}|{self.url}|{self.title}".encode()).hexdigest()
            self.id = digest[:12]

    def to_dict(self) -> dict:
        return asdict(self)


class JobChannel(Protocol):
    name: str

    def search(self, queries: list[str], *, limit: int) -> list[Job]: ...
