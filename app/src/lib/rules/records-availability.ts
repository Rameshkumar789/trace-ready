import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateRecordsAvailability(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-records-availability");
  if (!ruleCard) return [];
  const missingDocs = dataset.events.filter(
    (event) => !dataset.sourceDocuments.some((doc) => doc.eventId === event.eventId && doc.evidenceStatus === "available")
  );
  return missingDocs.map((event) =>
    createFinding({
      title: "Source document not linked to event",
      status: "missing_evidence",
      severity: "medium",
      findingType: "sortable_export_gap",
      eventId: event.eventId,
      expectedOrRequired: "Event-level source document or reference record evidence.",
      recommendation: "Link each CTE event to source documents so a sortable response package can be assembled.",
      ruleCardId: ruleCard.ruleCardId,
      ruleCardVersion: ruleCard.version,
      sourceChunkId: ruleCard.sourceChunkIds[0],
      evidenceRefs: [{ sheet: "09_Source_Documents", field: event.eventId }]
    })
  );
}
