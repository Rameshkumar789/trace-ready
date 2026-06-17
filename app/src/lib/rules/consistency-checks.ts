import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateConsistencyChecks(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-records-availability");
  if (!ruleCard) return [];
  const findings: Finding[] = [];
  const eventsById = new Map(dataset.events.map((event) => [event.eventId, event]));
  for (const line of dataset.lineItems) {
    if (!eventsById.has(line.eventId)) {
      findings.push(
        createFinding({
          title: "Line item references missing event",
          status: "operational_anomaly",
          severity: "medium",
          findingType: "orphan_line_item",
          eventId: line.eventId,
          eventLineId: line.eventLineId,
          recommendation: "Fix event_id links before relying on the export package.",
          ruleCardId: ruleCard.ruleCardId,
          ruleCardVersion: ruleCard.version,
          sourceChunkId: ruleCard.sourceChunkIds[0],
          evidenceRefs: [{ sheet: "06_Event_Line_Items", field: line.eventLineId }]
        })
      );
    }
  }
  return findings;
}
