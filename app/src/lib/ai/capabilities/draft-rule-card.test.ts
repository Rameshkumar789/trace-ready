import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { createManualRuleCardDraft, validateAiRuleCardDraft } from "./draft-rule-card";

describe("AI rule-card draft capability", () => {
  it("creates schema-valid draft-only rule card suggestions", () => {
    const { chunks } = loadRegulatoryBundle();
    const draft = createManualRuleCardDraft([chunks[0]], "entity_scope");
    const parsed = validateAiRuleCardDraft(draft);
    expect(parsed.success).toBe(true);
    expect(draft.requiresExpertReview).toBe(true);
  });
});
