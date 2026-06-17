import { randomUUID } from "node:crypto";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import type { TraceReadySession } from "@/lib/auth/session-cookie";
import type { Finding } from "@/lib/findings/finding";
import type { AuditPackagePin, Phase14GovernanceState, ReviewActionLogEntry, ReviewerOverride } from "@/lib/governance/types";

export type CustomerFindingReviewAction = "approve" | "reject" | "edit" | "assign" | "comment" | "request_more_evidence";

interface AuditProjectRow {
  id: string;
  customer_id: string | null;
  created_by_user_id: string | null;
}

interface AuditRunRow {
  id: string;
  rule_package_id: string | null;
  rule_package_version: number | null;
  rule_package_hash: string | null;
  parser_version: string | null;
  classifier_version: string | null;
  summary_json: unknown;
}

interface FindingRow {
  id: string;
  audit_project_id: string;
  audit_run_id: string | null;
  rule_card_id: string | null;
  rule_card_version: number | null;
  approved_record_id: string | null;
  approved_obligation_id: string | null;
  review_state: string;
  metadata_json: unknown;
}

interface ReviewActionRow {
  id: string;
  audit_project_id: string;
  audit_run_id: string | null;
  finding_id: string | null;
  action: string;
  actor_email: string | null;
  actor_role: string;
  reason: string;
  comment: string | null;
  before_json: unknown;
  after_json: unknown;
  created_at: string;
}

export async function applyCustomerFindingReviewAction(input: {
  auditId: string;
  findingId: string;
  action: CustomerFindingReviewAction;
  reason: string;
  comment?: string;
  assignedRole?: string;
  session: TraceReadySession;
}) {
  if (!input.reason.trim()) throw new Error("Review actions require a reason.");
  const client = createSupabaseAdminClient();
  const { run, finding } = await loadWritableFindingContext(client, input.auditId, input.findingId, input.session);
  const beforeReviewState = toReviewState(finding.review_state);
  const afterReviewState = nextReviewState(beforeReviewState, input.action);
  if (afterReviewState !== beforeReviewState) {
    await updateOrThrow(
      client
        .from("audit_findings")
        .update({
          review_state: afterReviewState,
          metadata_json: {
            ...asRecord(finding.metadata_json),
            lastCustomerReviewAction: input.action,
            lastCustomerReviewAt: new Date().toISOString()
          }
        })
        .eq("id", finding.id)
    );
  }
  await insertReviewAction({
    auditProjectId: input.auditId,
    auditRunId: finding.audit_run_id ?? run?.id,
    findingId: finding.id,
    action: input.action,
    reason: input.reason,
    comment: input.comment,
    beforeJson: { reviewState: beforeReviewState },
    afterJson: {
      reviewState: afterReviewState,
      assignedRole: input.assignedRole,
      currentRulePackageId: run?.rule_package_id,
      currentRulePackageVersion: run?.rule_package_version
    },
    session: input.session
  });
}

export async function createCustomerReviewerOverride(input: {
  auditId: string;
  findingId: string;
  reason: string;
  session: TraceReadySession;
}) {
  if (!input.reason.trim()) throw new Error("Overrides require a reason.");
  const client = createSupabaseAdminClient();
  const { run, finding } = await loadWritableFindingContext(client, input.auditId, input.findingId, input.session);
  await insertReviewAction({
    auditProjectId: input.auditId,
    auditRunId: finding.audit_run_id ?? run?.id,
    findingId: finding.id,
    action: "override",
    reason: input.reason,
    beforeJson: { reviewState: toReviewState(finding.review_state) },
    afterJson: {
      status: "excluded_from_automation",
      ruleCardId: finding.rule_card_id ?? finding.approved_record_id ?? finding.approved_obligation_id
    },
    session: input.session
  });
}

export async function promoteCustomerReviewerOverride(input: {
  auditId: string;
  overrideId: string;
  reason: string;
  session: TraceReadySession;
}) {
  if (!input.reason.trim()) throw new Error("Override promotion requires an approval reason.");
  const client = createSupabaseAdminClient();
  const project = await loadAuthorizedProject(client, input.auditId, input.session);
  if (!project) throw new Error(`Audit not found or not accessible: ${input.auditId}`);
  const override = await selectMaybe<ReviewActionRow>(
    client
      .from("customer_review_actions")
      .select("id, audit_project_id, audit_run_id, finding_id, action, actor_email, actor_role, reason, comment, before_json, after_json, created_at")
      .eq("audit_project_id", input.auditId)
      .eq("id", input.overrideId)
      .eq("action", "override")
      .maybeSingle()
  );
  if (!override) throw new Error(`Override not found: ${input.overrideId}`);
  await insertReviewAction({
    auditProjectId: input.auditId,
    auditRunId: override.audit_run_id,
    findingId: override.finding_id ?? undefined,
    action: "promote_override",
    reason: input.reason,
    beforeJson: { overrideId: override.id, status: "excluded_from_automation" },
    afterJson: { overrideId: override.id, status: "promoted_by_approval" },
    session: input.session
  });
}

export async function loadCustomerReviewGovernance(auditId: string, session: TraceReadySession): Promise<Phase14GovernanceState | undefined> {
  const client = createSupabaseAdminClient();
  const project = await loadAuthorizedProject(client, auditId, session);
  if (!project) return undefined;
  const [run, actions] = await Promise.all([
    selectMaybe<AuditRunRow>(
      client
        .from("audit_runs")
        .select("id, rule_package_id, rule_package_version, rule_package_hash, parser_version, classifier_version, summary_json")
        .eq("audit_project_id", auditId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    ),
    selectMany<ReviewActionRow>(
      client
        .from("customer_review_actions")
        .select("id, audit_project_id, audit_run_id, finding_id, action, actor_email, actor_role, reason, comment, before_json, after_json, created_at")
        .eq("audit_project_id", auditId)
        .order("created_at", { ascending: true })
    )
  ]);
  return {
    packagePin: packagePinFromRun(run),
    reviewActionLog: actions.map(mapReviewAction),
    reviewerOverrides: overridesFromActions(actions)
  };
}

async function loadWritableFindingContext(
  client: ReturnType<typeof createSupabaseAdminClient>,
  auditId: string,
  findingId: string,
  session: TraceReadySession
) {
  const project = await loadAuthorizedProject(client, auditId, session);
  if (!project) throw new Error(`Audit not found or not accessible: ${auditId}`);
  const [run, finding] = await Promise.all([
    selectMaybe<AuditRunRow>(
      client
        .from("audit_runs")
        .select("id, rule_package_id, rule_package_version, rule_package_hash, parser_version, classifier_version, summary_json")
        .eq("audit_project_id", auditId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    ),
    selectMaybe<FindingRow>(
      client
        .from("audit_findings")
        .select("id, audit_project_id, audit_run_id, rule_card_id, rule_card_version, approved_record_id, approved_obligation_id, review_state, metadata_json")
        .eq("audit_project_id", auditId)
        .eq("id", findingId)
        .maybeSingle()
    )
  ]);
  if (!finding) throw new Error(`Finding not found: ${findingId}`);
  return { project, run, finding };
}

async function insertReviewAction(input: {
  auditProjectId: string;
  auditRunId?: string | null;
  findingId?: string;
  action: ReviewActionLogEntry["action"];
  reason: string;
  comment?: string;
  beforeJson: Record<string, unknown>;
  afterJson: Record<string, unknown>;
  session: TraceReadySession;
}) {
  const client = createSupabaseAdminClient();
  await insertOrThrow(
    client.from("customer_review_actions").insert({
      id: `review_${randomUUID().replace(/-/g, "")}`,
      audit_project_id: input.auditProjectId,
      audit_run_id: input.auditRunId ?? null,
      finding_id: input.findingId ?? null,
      action: input.action,
      actor_user_id: input.session.userId,
      actor_email: input.session.email,
      actor_role: input.session.role,
      reason: input.reason.trim(),
      comment: input.comment?.trim() || null,
      before_json: input.beforeJson,
      after_json: input.afterJson
    })
  );
}

async function loadAuthorizedProject(client: ReturnType<typeof createSupabaseAdminClient>, auditId: string, session: TraceReadySession) {
  const project = await selectMaybe<AuditProjectRow>(
    client.from("audit_projects").select("id, customer_id, created_by_user_id").eq("id", auditId).maybeSingle()
  );
  if (!project) return undefined;
  if (session.role === "founder_admin" || project.created_by_user_id === session.userId) return project;
  if (!project.customer_id) return undefined;
  const membership = await selectMaybe<{ id: string }>(
    client
      .from("customer_memberships")
      .select("id")
      .eq("customer_id", project.customer_id)
      .eq("user_id", session.userId)
      .eq("status", "active")
      .maybeSingle()
  );
  return membership ? project : undefined;
}

function nextReviewState(current: Finding["reviewState"], action: CustomerFindingReviewAction): Finding["reviewState"] {
  if (action === "approve") return "approved";
  if (action === "reject") return "dismissed";
  if (action === "edit") return "edited";
  if (action === "request_more_evidence") return "needs_more_evidence";
  return current;
}

function packagePinFromRun(run?: AuditRunRow): AuditPackagePin {
  const summary = asRecord(run?.summary_json);
  return {
    rulePackageId: run?.rule_package_id ?? "approved-rule-package-v1",
    rulePackageVersion: run?.rule_package_version ?? 1,
    rulePackageHash: run?.rule_package_hash ?? undefined,
    scenarioRegressionStatus: stringFrom(summary.scenarioGateStatus) ?? "unknown",
    customerEvidenceVersion: stringFrom(summary.customerEvidenceVersion) ?? "db-backed",
    parserVersions: [run?.parser_version, run?.classifier_version].filter((value): value is string => Boolean(value)),
    modelVersions: ["none-live-model-output"],
    generatedAt: new Date().toISOString()
  };
}

function mapReviewAction(row: ReviewActionRow): ReviewActionLogEntry {
  const before = asRecord(row.before_json);
  const after = asRecord(row.after_json);
  return {
    actionId: row.id,
    auditId: row.audit_project_id,
    findingId: row.finding_id ?? undefined,
    reviewer: row.actor_email ?? row.actor_role,
    action: toReviewAction(row.action),
    reason: row.reason,
    comment: row.comment ?? undefined,
    assignedRole: stringFrom(after.assignedRole),
    createdAt: row.created_at,
    beforeReviewState: toOptionalReviewState(before.reviewState),
    afterReviewState: toOptionalReviewState(after.reviewState),
    immutable: true
  };
}

function overridesFromActions(rows: ReviewActionRow[]): ReviewerOverride[] {
  const promoted = new Map<string, string>();
  for (const row of rows.filter((item) => item.action === "promote_override")) {
    const after = asRecord(row.after_json);
    const overrideId = stringFrom(after.overrideId);
    if (overrideId) promoted.set(overrideId, row.id);
  }
  return rows
    .filter((row) => row.action === "override" && row.finding_id)
    .map((row) => {
      const after = asRecord(row.after_json);
      const promotedByActionId = promoted.get(row.id);
      return {
        overrideId: row.id,
        findingId: row.finding_id as string,
        ruleCardId: stringFrom(after.ruleCardId) ?? "approved-rule",
        reviewer: row.actor_email ?? row.actor_role,
        reason: row.reason,
        createdAt: row.created_at,
        status: promotedByActionId ? "promoted_by_approval" : "excluded_from_automation",
        promotedByActionId
      };
    });
}

export const customerReviewDbTestHelpers = {
  nextReviewState,
  overridesFromActions,
  mapReviewAction
};

function toReviewAction(value: string): ReviewActionLogEntry["action"] {
  if (
    value === "approve" ||
    value === "reject" ||
    value === "edit" ||
    value === "assign" ||
    value === "comment" ||
    value === "request_more_evidence" ||
    value === "override" ||
    value === "promote_override"
  ) {
    return value;
  }
  return "comment";
}

function toReviewState(value: string): Finding["reviewState"] {
  return value === "approved" || value === "edited" || value === "dismissed" || value === "needs_more_evidence" ? value : "pending";
}

function toOptionalReviewState(value: unknown): Finding["reviewState"] | undefined {
  return typeof value === "string" ? toReviewState(value) : undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function stringFrom(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

async function selectMaybe<T>(operation: PromiseLike<{ data: unknown; error: { message: string } | null }>): Promise<T | undefined> {
  const { data, error } = await operation;
  if (error) throw new Error(error.message);
  return (data as T | null) ?? undefined;
}

async function selectMany<T>(operation: PromiseLike<{ data: unknown; error: { message: string } | null }>): Promise<T[]> {
  const { data, error } = await operation;
  if (error) throw new Error(error.message);
  return (data as T[] | null) ?? [];
}

async function insertOrThrow(operation: PromiseLike<{ error: { message: string } | null }>) {
  const { error } = await operation;
  if (error) throw new Error(error.message);
}

async function updateOrThrow(operation: PromiseLike<{ error: { message: string } | null }>) {
  const { error } = await operation;
  if (error) throw new Error(error.message);
}
