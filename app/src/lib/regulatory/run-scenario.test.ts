import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { runScenario } from "./run-scenario";

describe("scenario runner", () => {
  it("passes approved scenario fixtures against approved rule cards", () => {
    const { scenarios, ruleCards } = loadRegulatoryBundle();
    const results = scenarios.map((scenario) => runScenario(scenario, ruleCards));
    expect(results.every((result) => result.passed)).toBe(true);
  });

  it("rejects unapproved rule cards", () => {
    const { scenarios, ruleCards } = loadRegulatoryBundle();
    const scenario = scenarios.find((item) => item.scenarioId === "scenario-missing-receiving-tlc")!;
    const tamperedCards = ruleCards.map((card) =>
      card.ruleCardId === "rule-receiving-kdes" ? { ...card, status: "draft" as const } : card
    );
    expect(runScenario(scenario, tamperedCards).passed).toBe(false);
  });
});
