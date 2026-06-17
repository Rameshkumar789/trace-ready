import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateTlcAssignment(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-tlc-lineage");
  if (!ruleCard) return [];
  return dataset.lineItems
    .filter((line) => !line.lotOrTlc && !line.outputLotOrTlc && !line.sourceLotOrTlc)
    .map((line) =>
      createFinding({
        title: "TLC missing from event line",
        status: "gap",
        severity: "high",
        findingType: "tlc_assignment_gap",
        eventId: line.eventId,
        eventLineId: line.eventLineId,
        fieldOrKde: "traceability_lot_code",
        expectedOrRequired: "TLC, input TLC, or output TLC where applicable.",
        recommendation: "Add TLC evidence or mark why this line is not applicable.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: [{ sheet: "06_Event_Line_Items", field: line.eventLineId }]
      })
    );
}
