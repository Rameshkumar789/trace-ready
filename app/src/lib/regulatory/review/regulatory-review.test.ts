import { describe, expect, it } from "vitest";
import type { RegulatoryDraft, RuleCard } from "../types";
import { approveDraftRuleCard, approveIntelligenceDraft, deprecateApprovedRuleCard, rejectIntelligenceDraft, rejectRegulatoryDraft } from "./regulatory-review-actions";
import { buildIntelligenceReviewQueue, buildRegulatoryReviewQueue } from "./regulatory-review-queue";

describe("regulatory expert review workflow", () => {
  const draft: RegulatoryDraft<Partial<RuleCard>> = {
    draftId: "draft-rule-shipping",
    draftType: "rule_card",
    sourceChunkIds: ["chunk-shipping-1340"],
    draft: {
      ruleArea: "cte_kde_completeness",
      cteType: "shipping",
      decisionQuestion: "Are shipping KDEs present?",
      deterministicLogic: "resolve_kde_requirements_by_cte",
      allowedFindingStates: ["pass", "gap", "missing_evidence"]
    },
    validationErrors: [],
    status: "ready_for_review",
    createdBy: "ai",
    createdAt: "2026-06-14T00:00:00.000Z"
  };

  it("queues valid drafts for FSMA expert review", () => {
    const queue = buildRegulatoryReviewQueue([draft]);
    expect(queue[0]?.readyForExpertReview).toBe(true);
  });

  it("approves drafts into executable versioned rule cards with reviewer metadata", () => {
    const { ruleCard, action } = approveDraftRuleCard(draft, "reviewer@example.com", "fsma_reviewer", "Matches source chunk.");
    expect(ruleCard.status).toBe("approved");
    expect(ruleCard.reviewedBy).toBe("reviewer@example.com");
    expect(ruleCard.sourceChunkIds).toEqual(["chunk-shipping-1340"]);
    expect(action.before).toEqual(draft);
  });

  it("rejects drafts and deprecates approved cards without mutating originals", () => {
    const rejected = rejectRegulatoryDraft(draft, "founder@example.com", "founder_admin", "Needs stronger citation.");
    expect(rejected.draft.status).toBe("rejected");
    expect(draft.status).toBe("ready_for_review");

    const { ruleCard } = approveDraftRuleCard(draft, "reviewer@example.com", "fsma_reviewer", "Approve.");
    const deprecated = deprecateApprovedRuleCard(ruleCard, "founder@example.com", "founder_admin", "Superseded.");
    expect(deprecated.ruleCard.status).toBe("deprecated");
    expect(deprecated.ruleCard.version).toBe(ruleCard.version + 1);
  });

  it("queues and approves validated intelligence records without mutating draft payloads", () => {
    const intelligenceDraft = {
      draft_id: "phase4_deterministic:defined_terms:term_traceability_lot_code",
      collection: "defined_terms",
      record_id: "term_traceability_lot_code",
      source_phase: "phase4_deterministic",
      extraction_method: "deterministic",
      confidence: "high",
      review_status: "needs_review" as const,
      source_chunk_ids: ["ecfr-21-cfr-1-subpart-s-21-cfr-1-1310-1"],
      citation_count: 1,
      citation_coverage_status: "complete",
      schema_valid: true,
      citation_valid: true,
      validation_errors: [],
      reviewer_blockers: [],
      payload: {
        term_id: "term_traceability_lot_code",
        term: "Traceability lot code",
        metadata: { review_status: "needs_review" }
      }
    };

    const queue = buildIntelligenceReviewQueue([intelligenceDraft]);
    expect(queue[0]?.readyForExpertReview).toBe(true);

    const { approvedRecord, action } = approveIntelligenceDraft(
      intelligenceDraft,
      "reviewer@example.com",
      "fsma_reviewer",
      "Citation and definition match eCFR source."
    );
    expect(approvedRecord.collection).toBe("defined_terms");
    expect(approvedRecord.payload.metadata).toMatchObject({ review_status: "approved" });
    expect(action.action).toBe("approve_intelligence_record");

    const rejected = rejectIntelligenceDraft(intelligenceDraft, "reviewer@example.com", "fsma_reviewer", "Needs narrower support span.");
    expect(rejected.draft.review_status).toBe("rejected");
    expect(intelligenceDraft.review_status).toBe("needs_review");
  });
});
