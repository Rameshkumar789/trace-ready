import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { deprecateRuleCard } from "./rule-card-workflow";

describe("rule card workflow", () => {
  it("preserves version and review history when changing rule-card status", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const result = deprecateRuleCard(ruleCards[0], "founder", "Superseded by test");
    expect(result.ruleCard.status).toBe("deprecated");
    expect(result.review.statusBefore).toBe(ruleCards[0].status);
    expect(result.version.snapshotJson.ruleCardId).toBe(ruleCards[0].ruleCardId);
  });
});
