import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type { RuleCard } from "@/lib/regulatory/types";
import { createFinding, type Finding } from "@/lib/findings/finding";

export function evaluateEntityScope(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-entity-scope");
  if (!ruleCard) return [];
  return dataset.businessProfiles
    .filter((profile) => profile.coveredEntityStatus === "not_determined")
    .map((profile) =>
      createFinding({
        title: "Business/entity scope cannot be determined",
        status: "not_determined",
        severity: "medium",
        findingType: "entity_scope_not_determined",
        observedValue: profile.businessType,
        expectedOrRequired: "Covered, exempt, partially exempt, or not covered with evidence.",
        recommendation: "Provide entity role, activity, FTL handling, and exemption evidence.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: profile.evidenceRefs
      })
    );
}

export function evaluateProductScope(dataset: NormalizedAuditDataset, ruleCards: RuleCard[]): Finding[] {
  const ruleCard = ruleCards.find((card) => card.ruleCardId === "rule-product-scope");
  if (!ruleCard) return [];
  return dataset.productScopeDecisions
    .filter((decision) => decision.status === "not_determined")
    .map((decision) =>
      createFinding({
        title: "Product FTL scope cannot be determined",
        status: "not_determined",
        severity: "medium",
        findingType: "product_scope_not_determined",
        observedValue: decision.productId,
        expectedOrRequired: "Clear product description and FTL category mapping.",
        recommendation: "Clarify product category and whether a same-form or exemption pathway applies.",
        ruleCardId: ruleCard.ruleCardId,
        ruleCardVersion: ruleCard.version,
        sourceChunkId: ruleCard.sourceChunkIds[0],
        evidenceRefs: decision.evidenceRefs
      })
    );
}
