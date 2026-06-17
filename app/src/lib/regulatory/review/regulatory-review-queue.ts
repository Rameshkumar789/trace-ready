import type { IntelligenceDraftReviewRecord, RegulatoryDraft, RuleCard } from "../types";

export interface RegulatoryReviewQueueItem<TDraft = unknown> {
  draft: RegulatoryDraft<TDraft>;
  blockers: string[];
  readyForExpertReview: boolean;
}

export function buildRegulatoryReviewQueue<TDraft>(drafts: RegulatoryDraft<TDraft>[]): RegulatoryReviewQueueItem<TDraft>[] {
  return drafts
    .filter((draft) => draft.status === "draft" || draft.status === "ready_for_review")
    .map((draft) => {
      const blockers = [
        draft.sourceChunkIds.length === 0 ? "Draft must cite at least one source chunk." : undefined,
        draft.validationErrors.length > 0 ? "Draft must pass schema validation before expert review." : undefined
      ].filter((blocker): blocker is string => Boolean(blocker));
      return {
        draft,
        blockers,
        readyForExpertReview: blockers.length === 0
      };
    });
}

export function approvedRuleCardsForPublication(ruleCards: RuleCard[]) {
  return ruleCards.filter((ruleCard) => ruleCard.status === "approved" && ruleCard.reviewedBy && ruleCard.reviewedAt);
}

export interface IntelligenceReviewQueueItem {
  draft: IntelligenceDraftReviewRecord;
  blockers: string[];
  readyForExpertReview: boolean;
}

export function buildIntelligenceReviewQueue(drafts: IntelligenceDraftReviewRecord[]): IntelligenceReviewQueueItem[] {
  return drafts
    .filter((draft) => draft.review_status === "needs_review" || draft.review_status === "draft")
    .map((draft) => {
      const blockers = [
        !draft.schema_valid ? "Draft must pass Pydantic schema validation." : undefined,
        !draft.citation_valid ? "Draft must have complete citation span validation." : undefined,
        draft.source_chunk_ids.length === 0 ? "Draft must cite at least one source chunk." : undefined,
        ...draft.reviewer_blockers
      ].filter((blocker): blocker is string => Boolean(blocker));

      return {
        draft,
        blockers,
        readyForExpertReview: blockers.length === 0
      };
    });
}
