import type { Finding } from "@/lib/findings/finding";

export interface ReviewQueueItem {
  finding: Finding;
  reviewState: Finding["reviewState"];
  reason: string;
}

export function createReviewQueue(findings: Finding[]) {
  return {
    items: findings
      .filter((finding) => finding.status !== "pass" && finding.status !== "not_applicable")
      .map<ReviewQueueItem>((finding) => ({
        finding,
        reviewState: finding.reviewState,
        reason: finding.status === "not_determined" ? "Needs business context or evidence." : "Review before customer report."
      }))
  };
}
