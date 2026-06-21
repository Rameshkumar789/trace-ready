from __future__ import annotations

from enum import Enum

from .._compat import BaseModel


class AuthorityRank(str, Enum):
    CODIFIED_RULE = "codified_rule"
    FINAL_RULE = "final_rule"
    FEDERAL_REGISTER_NOTICE = "federal_register_notice"
    GUIDANCE = "guidance"
    FAQ = "faq"
    TEMPLATE = "template"
    SCENARIO = "scenario"
    TRAINING = "training"
    RESEARCH = "research"
    MARKET_IMPACT = "market_impact"
    CHANGE_MONITOR = "change_monitor"
    CROSS_REFERENCE = "cross_reference"
    SUPPORT = "support"


class SourceStatus(str, Enum):
    INGESTED = "ingested"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    FAILED = "failed"
    INDEXED = "indexed"
    SUPERSEDED = "superseded"


class SourceType(str, Enum):
    CFR = "cfr"
    ECFR = "ecfr"
    FEDERAL_REGISTER = "federal_register"
    FDA_HTML = "fda_html"
    FDA_PDF = "fda_pdf"
    FDA_XLSX = "fda_xlsx"
    FDA_WEB_APP = "fda_web_app"
    LOCAL_DOCUMENT = "local_document"
    UNKNOWN = "unknown"


class CanonicalSourceRecord(BaseModel):
    source_id: str
    title: str
    url: str
    source_type: str
    authority_rank: str
    source_status: str
    source_tier: str | None = None
    source_use: str | None = None
    content_type: str | None = None
    effective_date: str | None = None
    compliance_date: str | None = None
    retrieved_at: str | None = None
    raw_hash: str | None = None
    raw_artifact_path: str | None = None
    normalized_artifact_path: str | None = None
    sections_extracted: int = 0
    chunks_count: int = 0
    rejected_chunks_count: int = 0
    manifest_sources: list[str] = []
    duplicate_source_ids: list[str] = []
    notes: list[str] = []


class CanonicalSourceChunk(BaseModel):
    chunk_id: str
    source_id: str
    section_label: str
    section_ref: str
    page_number: int | None = None
    text: str
    text_hash: str
    citation_anchor: str
    authority_rank: str
    source_url: str
    source_type: str
    usage_role: str = "extraction"
    quality_flags: list[str] = []
    raw_artifact_path: str | None = None
    normalized_artifact_path: str | None = None


class SourceHealthIssue(BaseModel):
    issue_type: str
    severity: str
    source_id: str
    message: str
    artifact_path: str | None = None


class ChunkHealthIssue(BaseModel):
    issue_type: str
    severity: str
    source_id: str
    chunk_id: str
    message: str
