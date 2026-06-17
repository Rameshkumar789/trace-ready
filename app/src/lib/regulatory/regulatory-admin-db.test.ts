import { describe, expect, it } from "vitest";
import { arrayLength, blockersForDraft, countCustomerReviewQueue } from "./regulatory-admin-db";

describe("regulatory admin DB helpers", () => {
  it("counts json array fields defensively", () => {
    expect(arrayLength(["a", "b"])).toBe(2);
    expect(arrayLength("not-json-array")).toBe(0);
    expect(arrayLength(undefined)).toBe(0);
  });

  it("combines schema, citation, validation, and reviewer blockers", () => {
    const blockers = blockersForDraft({
      id: "draft_1",
      collection: "rule_cards",
      record_id: "rule_1",
      source_phase: "phase6",
      extraction_method: "ai_draft",
      confidence: "medium",
      review_status: "needs_review",
      source_chunk_ids: ["chunk_1"],
      citation_count: 1,
      citation_coverage_status: "partial",
      schema_valid: false,
      citation_valid: false,
      validation_errors: ["missing title"],
      reviewer_blockers: ["needs FSMA reviewer"]
    });

    expect(blockers).toEqual(["needs FSMA reviewer", "missing title", "schema invalid", "citation invalid"]);
  });

  it("counts only unresolved customer finding review items", () => {
    expect(
      countCustomerReviewQueue([
        { status: "gap", review_state: "pending" },
        { status: "missing_evidence", review_state: "needs_more_evidence" },
        { status: "gap", review_state: "approved" },
        { status: "pass", review_state: "pending" },
        { status: "not_applicable", review_state: "pending" }
      ])
    ).toBe(2);
  });
});
