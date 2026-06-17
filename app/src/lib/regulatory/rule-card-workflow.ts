import type { RuleCard } from "./types";
import { createRuleCardReview, type RuleCardReview } from "./rule-card-review";
import { snapshotRuleCard, type RuleCardVersion } from "./rule-card-version";

export interface RuleCardWorkflowResult {
  ruleCard: RuleCard;
  review: RuleCardReview;
  version: RuleCardVersion;
}

export function approveRuleCard(ruleCard: RuleCard, reviewer: string, notes: string): RuleCardWorkflowResult {
  const version = snapshotRuleCard(ruleCard, notes, reviewer);
  const approved: RuleCard = {
    ...ruleCard,
    status: "approved",
    reviewedBy: reviewer,
    reviewedAt: new Date().toISOString(),
    version: ruleCard.version + (ruleCard.status === "approved" ? 0 : 1)
  };
  return {
    ruleCard: approved,
    review: createRuleCardReview(ruleCard, "approved", "approve", reviewer, notes),
    version
  };
}

export function deprecateRuleCard(ruleCard: RuleCard, reviewer: string, notes: string): RuleCardWorkflowResult {
  const version = snapshotRuleCard(ruleCard, notes, reviewer);
  const deprecated: RuleCard = {
    ...ruleCard,
    status: "deprecated",
    reviewedBy: reviewer,
    reviewedAt: new Date().toISOString(),
    version: ruleCard.version + 1
  };
  return {
    ruleCard: deprecated,
    review: createRuleCardReview(ruleCard, "deprecated", "deprecate", reviewer, notes),
    version
  };
}
