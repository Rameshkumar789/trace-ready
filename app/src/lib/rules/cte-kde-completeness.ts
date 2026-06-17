import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { KdeRequirementRecord, RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";
import { resolveKdeRequirements } from "./kde-requirement-resolver";

export function evaluateCteKdeCompleteness(
  dataset: NormalizedAuditDataset,
  requirements: KdeRequirementRecord[],
  ruleCards: RuleCard[]
): Finding[] {
  const findings: Finding[] = [];
  for (const event of dataset.events) {
    const required = resolveKdeRequirements(requirements, event.eventType);
    for (const requirement of required) {
      const observed = dataset.kdeValues.find(
        (kde) => kde.eventId === event.eventId && kde.fieldKey === requirement.fieldKey && kde.value
      );
      if (!observed) {
        const ruleCard = ruleCards.find((card) => card.ruleCardId === requirement.ruleCardId);
        if (!ruleCard) continue;
        findings.push(
          createFinding({
            title: `Missing ${requirement.kdeName}`,
            status: "gap",
            severity: requirement.severityIfMissing,
            findingType: "missing_kde",
            eventId: event.eventId,
            fieldOrKde: requirement.fieldKey,
            expectedOrRequired: requirement.appliesWhen,
            recommendation: `Add ${requirement.kdeName} evidence for ${event.eventType}.`,
            ruleCardId: ruleCard.ruleCardId,
            ruleCardVersion: ruleCard.version,
            sourceChunkId: requirement.sourceChunkId,
            kdeRequirementId: requirement.kdeRequirementId,
            evidenceRefs: [{ sheet: "07_KDE_Values", field: requirement.fieldKey }]
          })
        );
      }
    }
  }
  return findings;
}
