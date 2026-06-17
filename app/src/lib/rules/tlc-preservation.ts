import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateTlcPreservation(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-tlc-lineage");
  if (!ruleCard) return [];
  const transformationEvents = new Set(dataset.events.filter((event) => event.eventType === "transformation").map((event) => event.eventId));
  return dataset.lineItems
    .filter((line) => line.sourceLotOrTlc && line.outputLotOrTlc && !transformationEvents.has(line.eventId))
    .map((line) =>
      createFinding({
        title: "TLC changed outside transformation",
        status: "conflict",
        severity: "high",
        findingType: "tlc_preservation_conflict",
        eventId: line.eventId,
        eventLineId: line.eventLineId,
        observedValue: line.outputLotOrTlc,
        expectedOrRequired: line.sourceLotOrTlc,
        recommendation: "Confirm whether a transformation or allowed TLC-change condition occurred.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: [{ sheet: "06_Event_Line_Items", field: line.eventLineId }]
      })
    );
}
