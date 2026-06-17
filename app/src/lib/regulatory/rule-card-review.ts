import type { RuleCard } from "./types";

export interface RuleCardReview {
  ruleCardId: string;
  reviewer: string;
  statusBefore: RuleCard["status"];
  statusAfter: RuleCard["status"];
  reviewDecision: "approve" | "request_changes" | "deprecate" | "reject";
  notes: string;
  createdAt: string;
}

export function createRuleCardReview(
  ruleCard: RuleCard,
  statusAfter: RuleCard["status"],
  reviewDecision: RuleCardReview["reviewDecision"],
  reviewer: string,
  notes: string
): RuleCardReview {
  return {
    ruleCardId: ruleCard.ruleCardId,
    reviewer,
    statusBefore: ruleCard.status,
    statusAfter,
    reviewDecision,
    notes,
    createdAt: new Date().toISOString()
  };
}
