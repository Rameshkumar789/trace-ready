import { describe, expect, it } from "vitest";
import { createFinding } from "./finding";

describe("finding model", () => {
  it("creates stable findings with pending review by default", () => {
    const finding = createFinding({
      title: "Missing TLC",
      status: "gap",
      severity: "high",
      findingType: "missing_kde",
      recommendation: "Add TLC evidence.",
      ruleCardId: "rule",
      ruleCardVersion: 1,
      sourceChunkId: "chunk",
      evidenceRefs: [{ sheet: "07_KDE_Values" }]
    });
    expect(finding.findingId).toBe("finding-rule");
    expect(finding.reviewState).toBe("pending");
  });
});
