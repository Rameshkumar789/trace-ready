import type { Finding } from "@/lib/findings/finding";

export function findingsToRows(findings: Finding[]) {
  return findings.map((finding) => ({
    finding_id: finding.findingId,
    status: finding.status,
    severity: finding.severity,
    finding_type: finding.findingType,
    event_id: finding.eventId ?? "",
    field_or_kde: finding.fieldOrKde ?? "",
    expected_or_required: finding.expectedOrRequired ?? "",
    recommendation: finding.recommendation,
    rule_card_id: finding.ruleCardId,
    rule_card_version: finding.ruleCardVersion,
    source_chunk_id: finding.sourceChunkId,
    review_state: finding.reviewState
  }));
}
