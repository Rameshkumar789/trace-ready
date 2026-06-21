from __future__ import annotations

import re

from .._compat import BaseModel
from .citation_anchor import CitationAnchor, build_citation_anchor
from ..versioning.hashing import sha256_text


class SourceChunkDraft(BaseModel):
    chunk_id: str
    source_id: str
    section_label: str
    section: str
    text: str
    summary: str
    citation: str
    text_hash: str
    anchors: list[CitationAnchor]


class RejectedSourceSection(BaseModel):
    source_id: str
    section_label: str
    section: str
    text: str
    reason: str


def chunk_legal_meaning(
    *,
    source_id: str,
    source_url: str,
    source_hash: str,
    retrieved_at: str,
    sections: list[dict],
) -> list[SourceChunkDraft]:
    chunks, rejected = _chunk_legal_meaning(source_id=source_id, source_url=source_url, source_hash=source_hash, retrieved_at=retrieved_at, sections=sections)
    if rejected:
        raise ValueError(rejected[0].reason)
    return chunks


def chunk_legal_meaning_with_rejections(
    *,
    source_id: str,
    source_url: str,
    source_hash: str,
    retrieved_at: str,
    sections: list[dict],
) -> tuple[list[SourceChunkDraft], list[RejectedSourceSection]]:
    return _chunk_legal_meaning(source_id=source_id, source_url=source_url, source_hash=source_hash, retrieved_at=retrieved_at, sections=sections)


def _chunk_legal_meaning(
    *,
    source_id: str,
    source_url: str,
    source_hash: str,
    retrieved_at: str,
    sections: list[dict],
) -> tuple[list[SourceChunkDraft], list[RejectedSourceSection]]:
    chunks: list[SourceChunkDraft] = []
    rejected: list[RejectedSourceSection] = []
    for index, section in enumerate(sections, start=1):
        text = str(section.get("text", "")).strip()
        if not text:
            continue
        section_ref = str(section.get("section") or section.get("section_label") or "document")
        try:
            _reject_split_condition(text)
        except ValueError as error:
            rejected.append(
                RejectedSourceSection(
                    source_id=source_id,
                    section_label=str(section.get("section_label") or section_ref),
                    section=section_ref,
                    text=text,
                    reason=str(error),
                )
            )
            continue
        anchor = build_citation_anchor(
            source_id=source_id,
            source_url=source_url,
            source_hash=source_hash,
            retrieved_at=retrieved_at,
            section=section_ref,
            paragraph=section.get("paragraph"),
            table_label=section.get("table_label"),
            page_number=section.get("page_number"),
        )
        chunks.append(
            SourceChunkDraft(
                chunk_id=f"{source_id}-{_slug(section_ref)}-{index}",
                source_id=source_id,
                section_label=str(section.get("section_label") or section_ref),
                section=section_ref,
                text=text,
                summary=_summary(text),
                citation=anchor.citation,
                text_hash=f"sha256:{sha256_text(source_hash + text)}",
                anchors=[anchor],
            )
        )
    return chunks, rejected


def _reject_split_condition(text: str) -> None:
    lower = text.lower()
    if len(lower) > 120:
        return
    if re.search(r"\b(if|when|unless|where|provided that)\b", lower) and not re.search(
        r"\b(must|shall|required|requires|maintain|keep|establish)\b", lower
    ):
        raise ValueError("Chunk has condition language without an obligation.")


def _summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= 180 else compact[:177] + "..."


def _slug(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))
