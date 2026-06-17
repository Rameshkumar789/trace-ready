import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { validateRuleCard } from "./validate-rule-card";

describe("rule card validation", () => {
  it("validates approved source-backed cards", () => {
    const { ruleCards, chunks } = loadRegulatoryBundle();
    const receiving = ruleCards.find((card) => card.ruleCardId === "rule-receiving-kdes")!;
    expect(validateRuleCard(receiving, chunks, true)).toEqual({ valid: true, errors: [] });
  });

  it("blocks draft cards from customer-facing use", () => {
    const { ruleCards, chunks } = loadRegulatoryBundle();
    const draft = { ...ruleCards[0], status: "draft" as const };
    expect(validateRuleCard(draft, chunks, true).valid).toBe(false);
  });

  it("blocks proposed-rule-only cards from final gap states", () => {
    const { ruleCards, chunks } = loadRegulatoryBundle();
    const proposed = ruleCards.find((card) => card.ruleCardId === "rule-proposed-extension-monitor")!;
    expect(validateRuleCard(proposed, chunks, true).valid).toBe(true);
    expect(proposed.allowedFindingStates).toEqual(["proposed_change", "needs_expert_review"]);
  });
});
