import type { Finding } from "@/lib/findings/finding";

interface AuditPackagePin {
  rulePackageId: string;
  rulePackageVersion: number;
  rulePackageHash?: string;
  scenarioRegressionStatus: string;
  customerEvidenceVersion: string;
  parserVersions: string[];
  modelVersions: string[];
  generatedAt: string;
}

interface ReviewActionLogEntry {
  actionId: string;
  auditId: string;
  findingId?: string;
  exceptionId?: string;
  reviewer: string;
  action: "approve" | "reject" | "edit" | "assign" | "comment" | "request_more_evidence" | "override" | "promote_override";
  reason: string;
  comment?: string;
  assignedRole?: string;
  createdAt: string;
  beforeReviewState?: Finding["reviewState"];
  afterReviewState?: Finding["reviewState"];
  immutable: true;
}

interface ReviewerOverride {
  overrideId: string;
  findingId: string;
  ruleCardId: string;
  reviewer: string;
  reason: string;
  createdAt: string;
  status: "excluded_from_automation" | "promoted_by_approval";
  promotedByActionId?: string;
}

export interface Phase14GovernanceState {
  packagePin: AuditPackagePin;
  reviewActionLog: ReviewActionLogEntry[];
  reviewerOverrides: ReviewerOverride[];
}
