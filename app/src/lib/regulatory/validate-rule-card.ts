import type { RuleCard, SourceChunk } from "./types";
import { ruleCardSchema } from "./rule-card";
import { findChunksByIds, chunkHasAuditCitation } from "./source-chunk";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateRuleCard(ruleCard: RuleCard, chunks: SourceChunk[], customerFacing = false): ValidationResult {
  const parsed = ruleCardSchema.safeParse(ruleCard);
  const errors: string[] = parsed.success ? [] : parsed.error.issues.map((issue) => issue.message);

  const linkedChunks = findChunksByIds(chunks, ruleCard.sourceChunkIds);
  if (linkedChunks.length !== ruleCard.sourceChunkIds.length) {
    errors.push("Rule card must link to existing source chunks.");
  }
  if (!linkedChunks.some(chunkHasAuditCitation)) {
    errors.push("Rule card must link to at least one active source chunk with citation and hash.");
  }
  if (ruleCard.status === "approved" && (!ruleCard.reviewedBy || !ruleCard.reviewedAt)) {
    errors.push("Approved rule card requires reviewer and reviewed date.");
  }
  if (customerFacing && ruleCard.status !== "approved") {
    errors.push("Customer-facing checks require approved rule cards.");
  }
  if (!ruleCard.isFinalizedSource && ruleCard.allowedFindingStates.includes("pass")) {
    errors.push("Non-final source rule cards cannot create final pass findings.");
  }
  if (!ruleCard.isFinalizedSource && ruleCard.allowedFindingStates.includes("gap")) {
    errors.push("Non-final source rule cards cannot create final gap findings.");
  }

  return { valid: errors.length === 0, errors };
}
