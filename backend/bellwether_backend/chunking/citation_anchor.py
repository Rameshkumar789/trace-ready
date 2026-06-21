from __future__ import annotations

from .._compat import BaseModel


class CitationAnchor(BaseModel):
    source_id: str
    citation: str
    section: str | None = None
    paragraph: str | None = None
    table_label: str | None = None
    page_number: int | None = None
    url: str | None = None
    retrieved_at: str | None = None
    source_hash: str | None = None


def build_citation_anchor(
    *,
    source_id: str,
    source_url: str,
    source_hash: str,
    retrieved_at: str,
    section: str,
    paragraph: str | None = None,
    table_label: str | None = None,
    page_number: int | None = None,
) -> CitationAnchor:
    citation = " ".join(part for part in [section, paragraph, table_label] if part)
    return CitationAnchor(
        source_id=source_id,
        citation=citation,
        section=section,
        paragraph=paragraph,
        table_label=table_label,
        page_number=page_number,
        url=source_url,
        retrieved_at=retrieved_at,
        source_hash=source_hash,
    )
