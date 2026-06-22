import type { Finding } from "@/lib/findings/finding";
import type { FindingSeverity, FindingState } from "@/lib/ontology/types";
import type { SupplierProductCoverageRow, SupplierScorecardRow } from "@/lib/report/supplier-scorecard";

/**
 * Client for the rebuilt /v2 backend (bellwether_core). Maps the lean API shapes onto the
 * existing UI types so the operator screens render against the new backend unchanged.
 */

interface V2FindingRow {
  id: string;
  severity: string;
  status: string;
  finding_type: string;
  title: string;
  message?: string | null;
  event_id?: string | null;
  cte?: string | null;
  field_or_kde?: string | null;
  recommendation?: string | null;
  citation_section?: string | null;
  citation_scenario?: string | null;
  citation_note?: string | null;
  confidence?: number | null;
  evidence_ids_json?: string[] | null;
  review_state?: string | null;
}

interface V2AuditResponse {
  run: { id: string; status: string; readiness_passed?: boolean; summary_json?: Record<string, unknown> };
  findings: V2FindingRow[];
  coverage: SupplierProductCoverageRow[];
  scorecards: SupplierScorecardRow[];
  anomalies: Array<{ anomaly_type: string; severity: string; status: string; reason: string }>;
}

export interface V2Audit {
  runId: string;
  readinessPassed: boolean;
  findings: Finding[];
  coverage: SupplierProductCoverageRow[];
  scorecards: SupplierScorecardRow[];
  anomalies: V2AuditResponse["anomalies"];
}

const SEVERITIES: ReadonlySet<string> = new Set(["low", "medium", "high", "critical"]);

function coerceSeverity(value: string): FindingSeverity {
  return (SEVERITIES.has(value) ? value : "medium") as FindingSeverity;
}

function mapFinding(row: V2FindingRow): Finding {
  return {
    findingId: row.id,
    title: row.title,
    status: row.status as FindingState,
    severity: coerceSeverity(row.severity),
    findingType: row.finding_type,
    eventId: row.event_id ?? undefined,
    fieldOrKde: row.field_or_kde ?? undefined,
    observedValue: undefined,
    expectedOrRequired: undefined,
    recommendation: row.recommendation ?? "",
    ruleCardId: "approved-rule",
    ruleCardVersion: 1,
    sourceChunkId: row.citation_section ?? "approved-source",
    approvedObligationId: undefined,
    sourceCitation: {
      section: row.citation_section ?? undefined,
      scenario: row.citation_scenario ?? undefined,
      note: row.citation_note ?? undefined,
    },
    evidenceRefs: [],
    reviewState: (row.review_state as Finding["reviewState"]) ?? "pending",
  };
}

export async function loadV2Audit(runId: string, baseUrl = ""): Promise<V2Audit> {
  const res = await fetch(`${baseUrl}/v2/audits/${encodeURIComponent(runId)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`v2 audit fetch failed: ${res.status}`);
  const body = (await res.json()) as V2AuditResponse;
  return {
    runId: body.run.id,
    readinessPassed: Boolean(body.run.readiness_passed),
    findings: body.findings.map(mapFinding),
    coverage: body.coverage ?? [],
    scorecards: body.scorecards ?? [],
    anomalies: body.anomalies ?? [],
  };
}
