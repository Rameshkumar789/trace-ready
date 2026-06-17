import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { createManualScenarioDraft, validateAiScenarioDraft } from "./draft-scenario-case";

describe("AI scenario draft capability", () => {
  it("creates schema-valid scenario drafts that require expert review", () => {
    const { chunks, ruleCards } = loadRegulatoryBundle();
    const draft = createManualScenarioDraft(ruleCards[0], [chunks[0]], "business scope");
    const parsed = validateAiScenarioDraft(draft);
    expect(parsed.success).toBe(true);
    expect(draft.expertReviewRequired).toBe(true);
  });
});
