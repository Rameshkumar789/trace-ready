import type { RuleCard } from "./types";

export interface RuleCardVersion {
  ruleCardId: string;
  version: number;
  snapshotJson: RuleCard;
  changeReason: string;
  changedBy: string;
  createdAt: string;
}

export function snapshotRuleCard(ruleCard: RuleCard, changeReason: string, changedBy: string): RuleCardVersion {
  return {
    ruleCardId: ruleCard.ruleCardId,
    version: ruleCard.version,
    snapshotJson: ruleCard,
    changeReason,
    changedBy,
    createdAt: new Date().toISOString()
  };
}
