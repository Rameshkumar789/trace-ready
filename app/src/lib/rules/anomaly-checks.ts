import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateAnomalies(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-records-availability");
  if (!ruleCard) return [];
  const duplicateReferences = new Map<string, number>();
  for (const event of dataset.events) {
    if (!event.referenceRecordNo) continue;
    duplicateReferences.set(event.referenceRecordNo, (duplicateReferences.get(event.referenceRecordNo) ?? 0) + 1);
  }
  return [...duplicateReferences.entries()]
    .filter(([, count]) => count > 1)
    .map(([reference]) =>
      createFinding({
        title: "Duplicate reference document",
        status: "operational_anomaly",
        severity: "low",
        findingType: "duplicate_reference",
        observedValue: reference,
        recommendation: "Review duplicate reference numbers before relying on the export package.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: [{ sheet: "05_CTE_Events", field: reference }]
      })
    );
}
