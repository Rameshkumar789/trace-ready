import type { IntelligenceDraftReviewRecord, RegulatoryDraft, RuleCard } from "../types";

export interface RegulatoryReviewAction {
  actionId: string;
  targetId: string;
  action:
    | "approve_rule_card"
    | "approve_intelligence_record"
    | "edit_and_approve_intelligence_record"
    | "edit_and_approve_rule_card"
    | "reject_draft"
    | "request_more_source_evidence"
    | "deprecate_approved_card"
    | "publish_new_version";
  reviewer: string;
  reviewerRole: "founder_admin" | "fsma_reviewer";
  reason: string;
  createdAt: string;
  before: unknown;
  after: unknown;
}

export interface ApprovedIntelligenceRecord {
  id: string;
  draftRecordId: string;
  collection: string;
  recordId: string;
  version: number;
  approvedBy: string;
  approvedAt: string;
  approvalReason: string;
  sourceChunkIds: string[];
  payload: Record<string, unknown>;
}

export function approveDraftRuleCard(
  draft: RegulatoryDraft<Partial<RuleCard>>,
  reviewer: string,
  reviewerRole: "founder_admin" | "fsma_reviewer",
  reason: string
): { ruleCard: RuleCard; action: RegulatoryReviewAction } {
  const now = new Date().toISOString();
  const ruleCard: RuleCard = {
    ruleCardId: draft.draft.ruleCardId ?? draft.draftId.replace(/^draft-/, "rule-"),
    ruleArea: draft.draft.ruleArea ?? "regulatory_review",
    cteType: draft.draft.cteType ?? null,
    decisionQuestion: draft.draft.decisionQuestion ?? "Reviewed regulatory rule card.",
    sourceChunkIds: draft.sourceChunkIds,
    authorityRank: draft.draft.authorityRank ?? 1,
    isFinalizedSource: draft.draft.isFinalizedSource ?? true,
    effectiveDate: draft.draft.effectiveDate ?? null,
    complianceDate: draft.draft.complianceDate ?? null,
    conditions: draft.draft.conditions ?? [],
    deterministicLogic: draft.draft.deterministicLogic ?? "manual_review_required",
    allowedFindingStates: draft.draft.allowedFindingStates ?? ["needs_expert_review"],
    status: "approved",
    reviewedBy: reviewer,
    reviewedAt: now,
    version: (draft.draft.version ?? 0) + 1
  };
  return {
    ruleCard,
    action: createAction(draft.draftId, "approve_rule_card", reviewer, reviewerRole, reason, draft, ruleCard, now)
  };
}

export function rejectRegulatoryDraft<TDraft>(
  draft: RegulatoryDraft<TDraft>,
  reviewer: string,
  reviewerRole: "founder_admin" | "fsma_reviewer",
  reason: string
) {
  const now = new Date().toISOString();
  const rejected = { ...draft, status: "rejected" as const };
  return {
    draft: rejected,
    action: createAction(draft.draftId, "reject_draft", reviewer, reviewerRole, reason, draft, rejected, now)
  };
}

export function deprecateApprovedRuleCard(
  ruleCard: RuleCard,
  reviewer: string,
  reviewerRole: "founder_admin" | "fsma_reviewer",
  reason: string
) {
  const now = new Date().toISOString();
  const deprecated: RuleCard = { ...ruleCard, status: "deprecated", reviewedBy: reviewer, reviewedAt: now, version: ruleCard.version + 1 };
  return {
    ruleCard: deprecated,
    action: createAction(ruleCard.ruleCardId, "deprecate_approved_card", reviewer, reviewerRole, reason, ruleCard, deprecated, now)
  };
}

export function approveIntelligenceDraft(
  draft: IntelligenceDraftReviewRecord,
  reviewer: string,
  reviewerRole: "founder_admin" | "fsma_reviewer",
  reason: string,
  editedPayload?: Record<string, unknown>
): { approvedRecord: ApprovedIntelligenceRecord; action: RegulatoryReviewAction } {
  if (draft.review_status !== "needs_review") {
    throw new Error("Only needs_review intelligence drafts can be approved.");
  }
  if (!draft.schema_valid || !draft.citation_valid || draft.reviewer_blockers.length > 0) {
    throw new Error("Intelligence draft must pass schema, citation, and blocker checks before approval.");
  }

  const now = new Date().toISOString();
  const approvedRecord: ApprovedIntelligenceRecord = {
    id: `approved:${draft.collection}:${draft.record_id}:v1`,
    draftRecordId: draft.draft_id,
    collection: draft.collection,
    recordId: draft.record_id,
    version: 1,
    approvedBy: reviewer,
    approvedAt: now,
    approvalReason: reason,
    sourceChunkIds: draft.source_chunk_ids,
    payload: {
      ...(editedPayload ?? draft.payload),
      metadata: {
        ...((editedPayload ?? draft.payload).metadata as Record<string, unknown> | undefined),
        review_status: "approved",
        reviewed_by: reviewer,
        reviewed_at: now
      }
    }
  };

  return {
    approvedRecord,
    action: createAction(
      draft.draft_id,
      editedPayload ? "edit_and_approve_intelligence_record" : "approve_intelligence_record",
      reviewer,
      reviewerRole,
      reason,
      draft,
      approvedRecord,
      now
    )
  };
}

export function rejectIntelligenceDraft(
  draft: IntelligenceDraftReviewRecord,
  reviewer: string,
  reviewerRole: "founder_admin" | "fsma_reviewer",
  reason: string
) {
  const now = new Date().toISOString();
  const rejected = { ...draft, review_status: "rejected" as const, reviewer_blockers: [...draft.reviewer_blockers, reason] };
  return {
    draft: rejected,
    action: createAction(draft.draft_id, "reject_draft", reviewer, reviewerRole, reason, draft, rejected, now)
  };
}

function createAction(
  targetId: string,
  action: RegulatoryReviewAction["action"],
  reviewer: string,
  reviewerRole: RegulatoryReviewAction["reviewerRole"],
  reason: string,
  before: unknown,
  after: unknown,
  createdAt: string
): RegulatoryReviewAction {
  return {
    actionId: `reg-review-${createdAt}-${targetId}`,
    targetId,
    action,
    reviewer,
    reviewerRole,
    reason,
    createdAt,
    before,
    after
  };
}
