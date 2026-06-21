import type { Finding } from "@/lib/findings/finding";
import type { ReadinessGateResult } from "@/lib/regulatory/readiness-gate";

interface AuditReportInput {
  findings: Finding[];
  readinessGate: ReadinessGateResult;
}

export function generateAuditReport(audit: AuditReportInput) {
  const highPriority = audit.findings.filter((finding) => ["high", "critical"].includes(finding.severity));
  const notDetermined = audit.findings.filter((finding) =>
    ["not_determined", "cannot_determine", "needs_expert_review"].includes(finding.status)
  );

  const markdown = [
    "# Bellwether FSMA 204 Readiness Audit",
    "",
    "**Report status:** Draft readiness review",
    "",
    "This report is a readiness audit and is not legal certification.",
    "",
    "## Executive Readiness Summary",
    "",
    `- Findings: ${audit.findings.length}`,
    `- Readiness gate: ${audit.readinessGate.passed ? "passed" : "blocked"}`,
    `- High-priority gaps: ${highPriority.length}`,
    `- Not-determined items: ${notDetermined.length}`,
    "",
    "## Scope And Limitations",
    "",
    "Bellwether evaluated uploaded or sample event data against approved source-backed rule cards and approved KDE requirements. Areas without sufficient customer evidence are marked not determined instead of treated as pass/fail.",
    "",
    "## Source-System Readiness",
    "",
    "Bellwether reviews whether supplied Excel, EDI/ASN, ERP, WMS, traceability-platform exports, supplier documents, and manual records can carry the required KDE, CTE, TLC, source-reference, and sortable-export evidence. This section is not an integration promise; it shows which current sources can or cannot prove readiness.",
    "",
    "## Supplier Data Quality",
    "",
    "Bellwether separates supplier-provided gaps from internal mapping or system gaps. Supplier data quality should show missing KDEs, missing TLCs, inconsistent product/location/date/quantity fields, weak source-document references, and repeated issue patterns.",
    "",
    "## Imported And Multilingual Record Review",
    "",
    "Imported or non-English records are flagged for human review. Bellwether does not claim certified translation; blocked or ambiguous evidence is marked needs review or not determined before customer-facing findings are finalized.",
    "",
    "## Source Registry And Rule Versions",
    "",
    ...audit.findings.map(
      (finding) =>
        `- ${finding.findingId}: rule ${finding.ruleCardId} v${finding.ruleCardVersion}, source chunk ${finding.sourceChunkId}`
    ),
    "",
    "## High-Priority Gaps",
    "",
    ...(highPriority.length
      ? highPriority.map((finding) => `- **${finding.title}**: ${finding.recommendation}`)
      : ["- None in this draft run."]),
    "",
    "## Not-Determined Items",
    "",
    ...(notDetermined.length
      ? notDetermined.map((finding) => `- **${finding.title}**: ${finding.recommendation}`)
      : ["- None in this draft run."]),
    "",
    "## Findings",
    "",
    ...audit.findings.map(
      (finding) =>
        `- ${finding.status.toUpperCase()} / ${finding.severity}: ${finding.title}. ${finding.recommendation}`
    ),
    "",
    "## Remediation Plan",
    "",
    "1. Resolve missing TLC and KDE evidence first.",
    "2. Confirm entity, product, and exemption scope before removing obligations.",
    "3. Link every CTE event to source documents.",
    "4. Review not-determined items with an FSMA expert or customer operator.",
    "",
    "## Disclaimer",
    "",
    "Bellwether provides a readiness review based on supplied records, source-backed rule cards, deterministic checks, and human review. It does not provide legal certification."
  ].join("\n");

  return { markdown };
}
