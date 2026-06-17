import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import { traceabilityPlanMissingItems } from "@/lib/ontology/traceability-plan-types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateTraceabilityPlan(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-traceability-plan");
  if (!ruleCard) return [];
  return dataset.traceabilityPlans.flatMap((plan) =>
    traceabilityPlanMissingItems(plan).map((item) =>
      createFinding({
        title: `Traceability plan missing ${item}`,
        status: "missing_evidence",
        severity: "medium",
        findingType: "traceability_plan_gap",
        fieldOrKde: item,
        expectedOrRequired: "Traceability plan evidence required by the rule.",
        recommendation: `Add traceability plan evidence for ${item}.`,
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: plan.evidenceRefs
      })
    )
  );
}
