import type { ParsedWorkbook } from "@/lib/import/workbook-parser";
import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { Finding } from "@/lib/findings/finding";
import type { Phase14GovernanceState } from "@/lib/governance/types";
import type { ReadinessGateResult } from "@/lib/regulatory/readiness-gate";

export interface StoredAudit {
  auditId: string;
  createdAt: string;
  fileName: string;
  parseErrors: ParsedWorkbook["errors"];
  dataset: NormalizedAuditDataset;
  findings: Finding[];
  readinessGate: ReadinessGateResult;
  coverage: Array<{ area: string; status: string; reason: string }>;
  mode: "draft" | "customer_facing";
  governance?: Phase14GovernanceState;
}

export interface StoredAuditSummary {
  auditId: string;
  createdAt: string;
  fileName: string;
  findingsCount: number;
  blockerCount: number;
  mode: StoredAudit["mode"];
  readinessPassed: boolean;
}
