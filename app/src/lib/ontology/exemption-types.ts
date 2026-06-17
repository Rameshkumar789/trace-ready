import type { ExemptionClaim } from "./types";

export function exemptionNeedsReview(claim: ExemptionClaim) {
  return !claim.evidenceProvided || claim.decision === "not_determined";
}
