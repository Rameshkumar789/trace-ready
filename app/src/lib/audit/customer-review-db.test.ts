import { describe, expect, it } from "vitest";
import { customerReviewDbTestHelpers } from "./customer-review-db";

describe("customer review DB helpers", () => {
  it("maps review actions to deterministic finding review states", () => {
    expect(customerReviewDbTestHelpers.nextReviewState("pending", "approve")).toBe("approved");
    expect(customerReviewDbTestHelpers.nextReviewState("pending", "reject")).toBe("dismissed");
    expect(customerReviewDbTestHelpers.nextReviewState("pending", "edit")).toBe("edited");
    expect(customerReviewDbTestHelpers.nextReviewState("pending", "request_more_evidence")).toBe("needs_more_evidence");
    expect(customerReviewDbTestHelpers.nextReviewState("pending", "comment")).toBe("pending");
    expect(customerReviewDbTestHelpers.nextReviewState("needs_more_evidence", "assign")).toBe("needs_more_evidence");
  });

  it("reconstructs override status from append-only actions", () => {
    const rows = [
      {
        id: "review_override_1",
        audit_project_id: "audit_1",
        audit_run_id: "run_1",
        finding_id: "finding_1",
        action: "override",
        actor_email: "reviewer@example.com",
        actor_role: "fsma_reviewer",
        reason: "Customer supplied alternate evidence.",
        comment: null,
        before_json: { reviewState: "pending" },
        after_json: { status: "excluded_from_automation", ruleCardId: "rule_1" },
        created_at: "2026-06-16T00:00:00.000Z"
      },
      {
        id: "review_promote_1",
        audit_project_id: "audit_1",
        audit_run_id: "run_1",
        finding_id: "finding_1",
        action: "promote_override",
        actor_email: "reviewer@example.com",
        actor_role: "fsma_reviewer",
        reason: "Approved by reviewer.",
        comment: null,
        before_json: { overrideId: "review_override_1", status: "excluded_from_automation" },
        after_json: { overrideId: "review_override_1", status: "promoted_by_approval" },
        created_at: "2026-06-16T00:05:00.000Z"
      }
    ];

    expect(customerReviewDbTestHelpers.overridesFromActions(rows)).toEqual([
      {
        overrideId: "review_override_1",
        findingId: "finding_1",
        ruleCardId: "rule_1",
        reviewer: "reviewer@example.com",
        reason: "Customer supplied alternate evidence.",
        createdAt: "2026-06-16T00:00:00.000Z",
        status: "promoted_by_approval",
        promotedByActionId: "review_promote_1"
      }
    ]);
  });
});
