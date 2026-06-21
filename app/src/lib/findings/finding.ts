import type { EvidenceRef, FindingSeverity, FindingState } from "@/lib/ontology/types";

export interface Finding {
  findingId: string;
  title: string;
  status: FindingState;
  severity: FindingSeverity;
  findingType: string;
  eventId?: string;
  eventLineId?: string;
  fieldOrKde?: string;
  observedValue?: string;
  expectedOrRequired?: string;
  recommendation: string;
  ruleCardId: string;
  ruleCardVersion: number;
  sourceChunkId: string;
  kdeRequirementId?: string;
  regulatorySourceId?: string;
  approvedObligationId?: string;
  evidenceRefs: EvidenceRef[];
  reviewState: "pending" | "approved" | "edited" | "dismissed" | "needs_more_evidence";
}

export function createFinding(input: Omit<Finding, "findingId" | "reviewState"> & { findingId?: string; reviewState?: Finding["reviewState"] }): Finding {
  return {
    ...input,
    findingId: input.findingId ?? stableFindingId(input.ruleCardId, input.eventId, input.eventLineId, input.fieldOrKde),
    reviewState: input.reviewState ?? "pending"
  };
}

function stableFindingId(...parts: Array<string | undefined>) {
  return `finding-${parts.filter(Boolean).join("-").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}
