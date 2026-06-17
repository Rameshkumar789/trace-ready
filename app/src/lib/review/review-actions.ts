import type { Finding } from "@/lib/findings/finding";

export interface ReviewAction {
  reviewer: string;
  action: "approve" | "edit" | "dismiss" | "request_more_evidence";
  reason: string;
  createdAt: string;
  before: Finding;
  after: Finding;
}

export function approveFinding(finding: Finding, reviewer: string, reason: string): ReviewAction {
  const after = { ...finding, reviewState: "approved" as const };
  return {
    reviewer,
    action: "approve",
    reason,
    createdAt: new Date().toISOString(),
    before: finding,
    after
  };
}
