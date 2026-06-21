from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


class NonDurableStoreError(RuntimeError):
    pass


def _is_production_like(environ: Mapping[str, str]) -> bool:
    env = environ.get("BELLWETHER_ENV") or environ.get("VERCEL_ENV")
    return env != "test"


@dataclass
class InMemoryDraftStore:
    sources: list[dict] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)
    rule_card_drafts: list[dict] = field(default_factory=list)
    kde_requirement_drafts: list[dict] = field(default_factory=list)
    environ: Mapping[str, str] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        env = os.environ if self.environ is None else self.environ
        if _is_production_like(env):
            raise NonDurableStoreError(
                "InMemoryDraftStore is test-only. Use Supabase tables for runtime."
            )

    def insert_source(self, source: dict) -> None:
        self.sources.append(source)

    def insert_chunks(self, chunks: list[dict]) -> None:
        self.chunks.extend(chunks)

    def insert_rule_card_draft(self, draft: dict) -> None:
        self.rule_card_drafts.append(draft)

    def insert_kde_requirement_draft(self, draft: dict) -> None:
        self.kde_requirement_drafts.append(draft)
