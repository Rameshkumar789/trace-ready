import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateExemptionClaims(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-exemption-claims");
  if (!ruleCard) return [];
  return dataset.exemptionClaims
    .filter((claim) => !claim.evidenceProvided)
    .map((claim) =>
      createFinding({
        title: `Exemption claim needs evidence: ${claim.claimType}`,
        status: "not_determined",
        severity: "medium",
        findingType: "exemption_evidence_missing",
        observedValue: claim.claimType,
        expectedOrRequired: "Official or business evidence supporting the exemption or partial exemption.",
        recommendation: "Attach exemption basis and supporting evidence before removing CTE/KDE obligations.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: claim.evidenceRefs
      })
    );
}
