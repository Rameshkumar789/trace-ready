"""Bellwether core — clean domain models (ground-up rebuild).

Lean, presentation-friendly shapes that the API/UI consume. Deliberately decoupled from the
legacy Phase11 internal models: the pipeline maps the validated engine output into these.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    section: str | None = None
    scenario: str | None = None  # flexibility scenario, if any
    note: str | None = None


class Finding(BaseModel):
    id: str
    severity: str  # low | medium | high | critical
    status: str  # gap | operational_anomaly | needs_review | pass | ...
    finding_type: str
    title: str
    message: str | None = None
    event_id: str | None = None
    cte: str | None = None
    field_or_kde: str | None = None
    recommendation: str | None = None
    citation: Citation = Field(default_factory=Citation)
    confidence: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class CoverageCell(BaseModel):
    supplier_id: str
    product: str
    ftl_status: str  # on | investigate | off
    event_count: int
    gap_count: int
    tlc_gap: bool
    status: str  # covered | gap | out_of_scope


class ScorecardAction(BaseModel):
    field_or_issue: str
    action: str
    citation: str | None = None


class SupplierScorecard(BaseModel):
    supplier_id: str
    supplier_name: str | None = None
    grade: str
    in_scope_products: int
    products_with_gaps: int
    tlc_gap: bool
    recommended_actions: list[ScorecardAction] = Field(default_factory=list)


class Anomaly(BaseModel):
    anomaly_type: str
    severity: str
    status: str
    reason: str
    details: dict = Field(default_factory=dict)


class AuditResult(BaseModel):
    """Everything one audit run produces, in clean shapes."""

    findings: list[Finding] = Field(default_factory=list)
    coverage: list[CoverageCell] = Field(default_factory=list)
    scorecards: list[SupplierScorecard] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    readiness_passed: bool = False
    summary: dict = Field(default_factory=dict)
