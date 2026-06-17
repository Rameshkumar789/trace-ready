import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateTlcLineage(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-tlc-lineage");
  if (!ruleCard) return [];
  return dataset.lineage
    .filter((lineage) => lineage.lineageStatus === "gap" || lineage.lineageStatus === "conflicting")
    .map((lineage) =>
      createFinding({
        title: "TLC lineage gap",
        status: lineage.lineageStatus === "conflicting" ? "conflict" : "gap",
        severity: "high",
        findingType: "lineage_gap",
        eventId: lineage.targetEventId,
        observedValue: lineage.sourceLotOrTlc,
        expectedOrRequired: lineage.targetLotOrTlc,
        recommendation: "Link input and output TLC evidence across receiving, transformation, and shipping records.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: [{ sheet: "08_TLC_Lineage", field: lineage.lineageId }]
      })
    );
}
