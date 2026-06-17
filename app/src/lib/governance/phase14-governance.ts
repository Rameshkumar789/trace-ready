import type { Finding } from "@/lib/findings/finding";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import type { AuditPackagePin, ExplainabilityTrace, Phase14GovernanceState, ReviewActionLogEntry, ReviewerOverride } from "./types";

export interface GovernanceInputs {
  rulePackage?: {
    package_id?: string;
    version?: number;
    package_hash?: string;
    scenario_regression_gate?: { status?: string };
  };
  phase10Summary?: {
    generatedAt?: string;
    evidenceRecords?: number;
    eventNodes?: number;
  };
  phase13Summary?: {
    twoStageStatus?: string;
    subparagraphResolutionStatus?: string;
  };
}

export function buildAuditPackagePin(inputs: GovernanceInputs = {}): AuditPackagePin {
  const rulePackage = inputs.rulePackage ?? {};
  const phase10 = inputs.phase10Summary ?? {};
  const phase13 = inputs.phase13Summary ?? {};
  return {
    rulePackageId: rulePackage.package_id ?? "approved-rule-package-v1",
    rulePackageVersion: rulePackage.version ?? 1,
    rulePackageHash: rulePackage.package_hash,
    scenarioRegressionStatus: rulePackage.scenario_regression_gate?.status ?? "pass",
    customerEvidenceVersion: `phase10:${phase10.generatedAt ?? "unknown"}:${phase10.evidenceRecords ?? 0}:${phase10.eventNodes ?? 0}`,
    parserVersions: [
      "workbook-parser:v1",
      "ontology-mapper:v1",
      `phase13-two-stage:${phase13.twoStageStatus ?? "unknown"}`,
      `phase13-subparagraph:${phase13.subparagraphResolutionStatus ?? "unknown"}`
    ],
    modelVersions: ["none-live-model-output"],
    generatedAt: new Date().toISOString()
  };
}

export function initializePhase14Governance(auditId: string, inputs: GovernanceInputs = {}): Phase14GovernanceState {
  return {
    packagePin: buildAuditPackagePin(inputs),
    reviewActionLog: [
      {
        actionId: stableActionId(auditId, "pin", "system"),
        auditId,
        reviewer: "system",
        action: "comment",
        reason: "Initial package/version pin recorded at audit creation.",
        createdAt: new Date().toISOString(),
        immutable: true
      }
    ],
    reviewerOverrides: []
  };
}

export function ensurePhase14Governance(audit: StoredAudit, inputs: GovernanceInputs = {}): Phase14GovernanceState {
  return audit.governance ?? initializePhase14Governance(audit.auditId, inputs);
}

export function applyFindingReviewAction(
  audit: StoredAudit,
  input: {
    findingId: string;
    reviewer: string;
    action: ReviewActionLogEntry["action"];
    reason: string;
    comment?: string;
    assignedRole?: string;
  },
  inputs: GovernanceInputs = {}
): StoredAudit {
  if (!input.reason.trim()) {
    throw new Error("Review actions require a reason.");
  }
  const finding = audit.findings.find((candidate) => candidate.findingId === input.findingId);
  if (!finding) {
    throw new Error(`Finding not found: ${input.findingId}`);
  }
  const after = updateFindingReviewState(finding, input.action);
  const actionEntry: ReviewActionLogEntry = {
    actionId: stableActionId(audit.auditId, input.findingId, `${input.action}:${Date.now()}`),
    auditId: audit.auditId,
    findingId: input.findingId,
    reviewer: input.reviewer,
    action: input.action,
    reason: input.reason.trim(),
    comment: input.comment?.trim() || undefined,
    assignedRole: input.assignedRole?.trim() || undefined,
    createdAt: new Date().toISOString(),
    beforeReviewState: finding.reviewState,
    afterReviewState: after.reviewState,
    immutable: true
  };
  const governance = ensurePhase14Governance(audit, inputs);
  return {
    ...audit,
    findings: audit.findings.map((candidate) => (candidate.findingId === input.findingId ? after : candidate)),
    governance: {
      ...governance,
      reviewActionLog: [...governance.reviewActionLog, actionEntry]
    }
  };
}

export function applyReviewerOverride(
  audit: StoredAudit,
  input: {
    findingId: string;
    reviewer: string;
    reason: string;
  },
  inputs: GovernanceInputs = {}
): StoredAudit {
  if (!input.reason.trim()) {
    throw new Error("Overrides require a reason.");
  }
  const finding = audit.findings.find((candidate) => candidate.findingId === input.findingId);
  if (!finding) {
    throw new Error(`Finding not found: ${input.findingId}`);
  }
  const governance = ensurePhase14Governance(audit, inputs);
  const override: ReviewerOverride = {
    overrideId: stableActionId(audit.auditId, input.findingId, `override:${Date.now()}`),
    findingId: input.findingId,
    ruleCardId: finding.ruleCardId,
    reviewer: input.reviewer,
    reason: input.reason.trim(),
    createdAt: new Date().toISOString(),
    status: "excluded_from_automation"
  };
  const actionEntry: ReviewActionLogEntry = {
    actionId: override.overrideId,
    auditId: audit.auditId,
    findingId: input.findingId,
    reviewer: input.reviewer,
    action: "override",
    reason: input.reason.trim(),
    createdAt: override.createdAt,
    beforeReviewState: finding.reviewState,
    afterReviewState: finding.reviewState,
    immutable: true
  };
  return {
    ...audit,
    governance: {
      ...governance,
      reviewActionLog: [...governance.reviewActionLog, actionEntry],
      reviewerOverrides: [...governance.reviewerOverrides, override]
    }
  };
}

export function promoteReviewerOverride(
  audit: StoredAudit,
  input: {
    overrideId: string;
    reviewer: string;
    reason: string;
  },
  inputs: GovernanceInputs = {}
): StoredAudit {
  if (!input.reason.trim()) {
    throw new Error("Override promotion requires an approval reason.");
  }
  const governance = ensurePhase14Governance(audit, inputs);
  const override = governance.reviewerOverrides.find((candidate) => candidate.overrideId === input.overrideId);
  if (!override) {
    throw new Error(`Override not found: ${input.overrideId}`);
  }
  const actionId = stableActionId(audit.auditId, override.overrideId, `promote:${Date.now()}`);
  const actionEntry: ReviewActionLogEntry = {
    actionId,
    auditId: audit.auditId,
    findingId: override.findingId,
    reviewer: input.reviewer,
    action: "promote_override",
    reason: input.reason.trim(),
    createdAt: new Date().toISOString(),
    immutable: true
  };
  return {
    ...audit,
    governance: {
      ...governance,
      reviewActionLog: [...governance.reviewActionLog, actionEntry],
      reviewerOverrides: governance.reviewerOverrides.map((candidate) =>
        candidate.overrideId === input.overrideId
          ? { ...candidate, status: "promoted_by_approval", promotedByActionId: actionId }
          : candidate
      )
    }
  };
}

export function buildExplainabilityTraces(audit: StoredAudit): ExplainabilityTrace[] {
  return audit.findings.map((finding) => {
    const event = audit.dataset.events.find((candidate) => candidate.eventId === finding.eventId);
    const lineItem = audit.dataset.lineItems.find((candidate) => candidate.eventLineId === finding.eventLineId || candidate.eventId === finding.eventId);
    return {
      findingId: finding.findingId,
      steps: [
        {
          step: "customer_evidence",
          label: "Customer evidence",
          detail: finding.evidenceRefs.length
            ? finding.evidenceRefs.map((ref) => `${ref.sheet ?? "workbook"}${ref.row ? ` row ${ref.row}` : ""}${ref.field ? ` ${ref.field}` : ""}`).join("; ")
            : "No direct source cell was attached to this finding.",
          refs: finding.evidenceRefs.map((ref) => ref.evidenceId ?? `${ref.sheet ?? "workbook"}:${ref.row ?? ""}:${ref.field ?? ""}`)
        },
        {
          step: "normalized_event",
          label: "Normalized event",
          detail: event
            ? `${event.eventType} ${event.eventId}${event.eventDatetime ? ` on ${event.eventDatetime}` : ""}${lineItem ? ` for ${lineItem.productName}` : ""}`
            : "Finding is audit-level or workbook-level.",
          refs: [finding.eventId, finding.eventLineId].filter((value): value is string => Boolean(value))
        },
        {
          step: "deterministic_check",
          label: "Deterministic check",
          detail: `${finding.findingType}: ${finding.expectedOrRequired ?? finding.recommendation}`,
          refs: [finding.kdeRequirementId, finding.fieldOrKde].filter((value): value is string => Boolean(value))
        },
        {
          step: "approved_rule",
          label: "Approved rule",
          detail: `${finding.ruleCardId} v${finding.ruleCardVersion}`,
          refs: [finding.ruleCardId]
        },
        {
          step: "source_citation",
          label: "Source citation",
          detail: finding.regulatorySourceId ? `${finding.regulatorySourceId} / ${finding.sourceChunkId}` : finding.sourceChunkId,
          refs: [finding.regulatorySourceId, finding.sourceChunkId].filter((value): value is string => Boolean(value))
        }
      ]
    };
  });
}

function updateFindingReviewState(finding: Finding, action: ReviewActionLogEntry["action"]): Finding {
  if (action === "approve") return { ...finding, reviewState: "approved" };
  if (action === "reject") return { ...finding, reviewState: "dismissed" };
  if (action === "edit") return { ...finding, reviewState: "edited" };
  if (action === "request_more_evidence") return { ...finding, reviewState: "needs_more_evidence" };
  return finding;
}

function stableActionId(...parts: string[]) {
  return `act-${parts.join("-").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 96)}`;
}
