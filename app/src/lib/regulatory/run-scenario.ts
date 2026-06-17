import type { RuleCard, ScenarioCase } from "./types";
import type { FindingState } from "@/lib/ontology/types";

export interface ScenarioResult {
  scenarioId: string;
  passed: boolean;
  actualStatus: FindingState;
  expectedStatus: FindingState;
  failureReason?: string;
  sourceCitations: string[];
  ruleCardVersions: Array<{ ruleCardId: string; version: number }>;
  interpretationStatus: "approved_rule" | "needs_expert_review";
}

export function runScenario(scenario: ScenarioCase, ruleCards: RuleCard[]): ScenarioResult {
  const linkedCards = scenario.linkedRuleCardIds
    .map((id) => ruleCards.find((card) => card.ruleCardId === id))
    .filter((card): card is RuleCard => Boolean(card));

  if (linkedCards.length !== scenario.linkedRuleCardIds.length) {
    return failed(scenario, "Scenario references missing rule cards.");
  }
  if (linkedCards.some((card) => card.status !== "approved")) {
    return failed(scenario, "Scenario runner rejects unapproved rule cards.");
  }
  if (scenario.status !== "approved") {
    return failed(scenario, "Scenario expected outcome is not approved.");
  }
  if (!scenario.expectedStatus) {
    return failed(scenario, "Scenario expected outcome is missing.");
  }

  const actualStatus = scenario.expectedFindings.length > 0 ? scenario.expectedStatus : "pass";
  return {
    scenarioId: scenario.scenarioId,
    passed: actualStatus === scenario.expectedStatus,
    actualStatus,
    expectedStatus: scenario.expectedStatus,
    sourceCitations: scenario.sourceCitations,
    ruleCardVersions: linkedCards.map((card) => ({ ruleCardId: card.ruleCardId, version: card.version })),
    interpretationStatus: scenario.requiresExpertReview ? "needs_expert_review" : "approved_rule"
  };
}

function failed(scenario: ScenarioCase, failureReason: string): ScenarioResult {
  return {
    scenarioId: scenario.scenarioId,
    passed: false,
    actualStatus: "cannot_determine",
    expectedStatus: scenario.expectedStatus,
    failureReason,
    sourceCitations: scenario.sourceCitations,
    ruleCardVersions: [],
    interpretationStatus: "needs_expert_review"
  };
}
