import type { KdeRequirementRecord, RuleCard, SourceChunk } from "./types";
import { kdeRequirementSchema } from "./kde-requirement";

export function validateKdeRequirement(requirement: KdeRequirementRecord, chunks: SourceChunk[], ruleCards: RuleCard[]) {
  const parsed = kdeRequirementSchema.safeParse(requirement);
  const errors: string[] = parsed.success ? [] : parsed.error.issues.map((issue) => issue.message);
  const chunk = chunks.find((candidate) => candidate.chunkId === requirement.sourceChunkId);
  const ruleCard = ruleCards.find((candidate) => candidate.ruleCardId === requirement.ruleCardId);

  if (!chunk || chunk.status !== "active") {
    errors.push("KDE requirement must link to an active source chunk.");
  }
  if (!ruleCard) {
    errors.push("KDE requirement must link to a rule card.");
  }
  if (requirement.status === "approved" && (!requirement.reviewedBy || !requirement.reviewedAt)) {
    errors.push("Approved KDE requirement requires reviewer metadata.");
  }
  if (requirement.requiredStatus === "conditional" && requirement.appliesWhen.trim().length < 12) {
    errors.push("Conditional KDE requirement needs explicit appliesWhen text.");
  }

  return { valid: errors.length === 0, errors };
}

export function approvedKdeRequirementsForCte(requirements: KdeRequirementRecord[], cteType: string) {
  return requirements.filter((requirement) => requirement.cteType === cteType && requirement.status === "approved");
}
