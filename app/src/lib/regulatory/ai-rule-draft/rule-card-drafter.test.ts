import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "../data-loader";
import { createDeterministicKdeDraft } from "./kde-requirement-drafter";
import { createDeterministicRuleCardDraft, validateRuleCardDraft } from "./rule-card-drafter";

describe("regulatory AI draft pipeline", () => {
  it("creates schema-valid draft rule cards that cite source chunks and remain non-executable", () => {
    const { chunks } = loadRegulatoryBundle();
    const draft = createDeterministicRuleCardDraft(chunks.slice(0, 2), "entity_scope");
    const validation = validateRuleCardDraft(draft);

    expect(validation.success).toBe(true);
    expect(draft.sourceChunkIds).toEqual(chunks.slice(0, 2).map((chunk) => chunk.chunkId));
    expect(draft.requiresExpertReview).toBe(true);
  });

  it("creates schema-valid KDE drafts with applies-when logic", () => {
    const { chunks } = loadRegulatoryBundle();
    const chunk = chunks.find((item) => item.chunkId === "chunk-shipping-1340");
    expect(chunk).toBeTruthy();
    const draft = createDeterministicKdeDraft(chunk!, "shipping", "Ship date");

    expect(draft.sourceChunkId).toBe("chunk-shipping-1340");
    expect(draft.appliesWhen).toContain("shipping");
    expect(draft.requiresExpertReview).toBe(true);
  });
});
