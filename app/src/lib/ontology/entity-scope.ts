import type { BusinessProfile, CoveredEntityStatus, EvidenceRef } from "./types";

export function decideEntityScope(profile: BusinessProfile): {
  status: CoveredEntityStatus;
  reason: string;
  evidenceRefs: EvidenceRef[];
} {
  if (profile.coveredEntityStatus !== "not_determined") {
    return {
      status: profile.coveredEntityStatus,
      reason: "Entity scope supplied in the business profile.",
      evidenceRefs: profile.evidenceRefs
    };
  }
  if (profile.handlesFtlFoods === false) {
    return {
      status: "not_covered",
      reason: "Business profile states it does not handle FTL foods.",
      evidenceRefs: profile.evidenceRefs
    };
  }
  if (profile.handlesFtlFoods === true) {
    return {
      status: "not_determined",
      reason: "Business handles FTL foods, but role/exemption evidence is incomplete.",
      evidenceRefs: profile.evidenceRefs
    };
  }
  return {
    status: "not_determined",
    reason: "Business profile does not provide enough scope evidence.",
    evidenceRefs: profile.evidenceRefs
  };
}
