import { describe, expect, it } from "vitest";
import { createFinding } from "@/lib/findings/finding";
import { createReviewQueue } from "./review-queue";

describe("review queue", () => {
  it("stages only reviewable customer-impacting findings", () => {
    const queue = createReviewQueue([
      createFinding({
        title: "Missing TLC",
        status: "gap",
        severity: "high",
        findingType: "missing_tlc",
        recommendation: "Add TLC evidence.",
        ruleCardId: "rule-tlc",
        ruleCardVersion: 1,
        sourceChunkId: "chunk-tlc",
        evidenceRefs: [{ sheet: "05_CTE_Events", row: 2 }]
      }),
      createFinding({
        title: "Not applicable",
        status: "not_applicable",
        severity: "low",
        findingType: "not_applicable",
        recommendation: "No action.",
        ruleCardId: "rule-scope",
        ruleCardVersion: 1,
        sourceChunkId: "chunk-scope",
        evidenceRefs: [{ sheet: "01_Product_Master", row: 2 }]
      })
    ]);

    expect(queue.items).toHaveLength(1);
    expect(queue.items[0]?.reviewState).toBe("pending");
    expect(queue.items[0]?.reason).toContain("Review");
  });
});
