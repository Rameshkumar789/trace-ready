from __future__ import annotations

import re

from .schemas import KdeRequirementDraft
from ..chunking.legal_chunker import SourceChunkDraft


def draft_kde_requirement(chunk: SourceChunkDraft, cte_type: str, kde_name: str) -> KdeRequirementDraft:
    return KdeRequirementDraft(
        cte_type=cte_type,
        kde_name=kde_name,
        field_key=re.sub(r"(^_|_$)", "", re.sub(r"[^a-z0-9]+", "_", kde_name.lower())),
        required_status="conditional" if "when" in chunk.text.lower() else "required",
        applies_when=f"Applies when {cte_type} records are present and source chunk {chunk.chunk_id} applies.",
        source_chunk_id=chunk.chunk_id,
        severity_if_missing="high",
        uncertainty_notes=["Draft KDE only; expert approval required before executable use."],
    )
