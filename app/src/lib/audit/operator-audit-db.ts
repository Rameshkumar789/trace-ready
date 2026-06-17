import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import type { TraceReadySession } from "@/lib/auth/session-cookie";
import type { Finding } from "@/lib/findings/finding";
import type { FindingSeverity, FindingState, NormalizedAuditDataset, CTEType, EvidenceRef } from "@/lib/ontology/types";
import type { StoredAudit, StoredAuditSummary } from "@/lib/audit/stored-audit";

export interface OperatorAuditDashboard {
  totalAudits: number;
  queuedJobs: number;
  runningJobs: number;
  failedJobs: number;
  openFindings: number;
  readyExports: number;
  latestAudit?: OperatorAuditSummary;
}

export interface OperatorAuditSummary extends StoredAuditSummary {
  status: string;
  jobStatus?: string;
  readinessStatus?: string;
  updatedAt: string;
}

export interface OperatorAuditArtifact {
  body: Uint8Array;
  fileName: string;
  contentType: string;
}

interface ProjectRow {
  id: string;
  customer_id: string | null;
  customer_name: string | null;
  file_name: string;
  mode: string;
  status: string;
  created_by_user_id: string | null;
  dataset_json: unknown;
  parse_errors: unknown;
  created_at: string;
  updated_at: string;
}

interface RunRow {
  id: string;
  audit_project_id: string;
  status: string;
  mode: string;
  parser_version: string | null;
  classifier_version: string | null;
  rule_package_id: string | null;
  rule_package_version: number | null;
  rule_package_hash: string | null;
  summary_json: unknown;
  created_at: string;
  updated_at: string;
}

interface JobRow {
  id: string;
  audit_project_id: string;
  status: string;
  job_type: string;
  created_at: string;
  updated_at: string;
}

interface FindingRow {
  id: string;
  title: string;
  status: string;
  severity: string;
  finding_type: string;
  event_id: string | null;
  event_line_id: string | null;
  field_or_kde: string | null;
  observed_value: string | null;
  expected_or_required: string | null;
  recommendation: string;
  rule_card_id: string | null;
  rule_card_version: number | null;
  approved_record_id: string | null;
  approved_obligation_id: string | null;
  source_chunk_id: string | null;
  kde_requirement_id: string | null;
  rule_package_id: string | null;
  rule_package_version: number | null;
  check_code: string | null;
  evidence_refs_json: unknown;
  metadata_json: unknown;
  review_state: string;
  created_at: string;
}

interface NormalizedEventRow {
  id: string;
  source_row_key: string;
  event_type_claim: string | null;
  event_datetime: string | null;
  event_datetime_raw: string | null;
  actor_object_id: string | null;
  from_object_id: string | null;
  to_object_id: string | null;
  document_object_id: string | null;
  classified_ctes_json: unknown;
}

interface EvidenceItemRow {
  id: string;
  evidence_type: string;
  canonical_field: string | null;
  source_sheet: string | null;
  source_row_number: number | null;
  source_column: string | null;
  raw_value: string | null;
  normalized_value: string | null;
  review_status: string;
  metadata_json: unknown;
}

interface ArtifactRow {
  id: string;
  artifact_type: string;
  file_name: string;
  content_type: string;
  storage_bucket: string;
  storage_key: string;
  status: string;
  created_at: string;
}

const projectSelect =
  "id, customer_id, customer_name, file_name, mode, status, created_by_user_id, dataset_json, parse_errors, created_at, updated_at";

export async function loadOperatorAuditDashboard(session: TraceReadySession): Promise<OperatorAuditDashboard> {
  const summaries = await listOperatorAuditSummaries(session, 25);
  return {
    totalAudits: summaries.length,
    queuedJobs: summaries.filter((audit) => audit.jobStatus === "queued").length,
    runningJobs: summaries.filter((audit) => audit.jobStatus === "running").length,
    failedJobs: summaries.filter((audit) => audit.jobStatus === "failed").length,
    openFindings: summaries.reduce((sum, audit) => sum + audit.findingsCount, 0),
    readyExports: summaries.filter((audit) => audit.readinessPassed).length,
    latestAudit: summaries[0]
  };
}

export async function listOperatorAuditSummaries(session: TraceReadySession, limit = 50): Promise<OperatorAuditSummary[]> {
  const client = createSupabaseAdminClient();
  const projects = await listAccessibleProjects(client, session, limit);
  if (!projects.length) return [];

  const projectIds = projects.map((project) => project.id);
  const [runs, jobs, findings] = await Promise.all([
    selectMany<RunRow>(
      client
        .from("audit_runs")
        .select("id, audit_project_id, status, mode, parser_version, classifier_version, rule_package_id, rule_package_version, rule_package_hash, summary_json, created_at, updated_at")
        .in("audit_project_id", projectIds)
        .order("created_at", { ascending: false })
    ),
    selectMany<JobRow>(
      client
        .from("audit_jobs")
        .select("id, audit_project_id, status, job_type, created_at, updated_at")
        .in("audit_project_id", projectIds)
        .order("created_at", { ascending: false })
    ),
    selectMany<{ audit_project_id: string; status: string; severity: string }>(
      client.from("audit_findings").select("audit_project_id, status, severity").in("audit_project_id", projectIds)
    )
  ]);

  const latestRuns = latestByProject(runs);
  const latestJobs = latestByProject(jobs);
  const findingCounts = countFindings(findings);
  return projects.map((project) => {
    const run = latestRuns.get(project.id);
    const job = latestJobs.get(project.id);
    const counts = findingCounts.get(project.id) ?? { findings: 0, blockers: 0 };
    const readinessStatus = readinessStatusFromRun(run);
    return {
      auditId: project.id,
      createdAt: project.created_at,
      updatedAt: project.updated_at,
      fileName: project.file_name,
      findingsCount: counts.findings,
      blockerCount: counts.blockers,
      mode: project.mode === "customer_facing" ? "customer_facing" : "draft",
      readinessPassed: readinessStatus === "ready",
      status: run?.status ?? project.status,
      jobStatus: job?.status,
      readinessStatus
    };
  });
}

export async function loadOperatorStoredAudit(auditProjectId: string, session: TraceReadySession): Promise<StoredAudit | undefined> {
  const client = createSupabaseAdminClient();
  const project = await loadAuthorizedProject(client, auditProjectId, session);
  if (!project) return undefined;

  const run = await selectMaybe<RunRow>(
    client
      .from("audit_runs")
      .select("id, audit_project_id, status, mode, parser_version, classifier_version, rule_package_id, rule_package_version, rule_package_hash, summary_json, created_at, updated_at")
      .eq("audit_project_id", auditProjectId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle()
  );

  const runFilterId = run?.id;
  const [findings, normalizedEvents, evidenceItems] = await Promise.all([
    selectMany<FindingRow>(
      findingQuery(client, auditProjectId, runFilterId)
    ),
    selectMany<NormalizedEventRow>(
      normalizedEventQuery(client, auditProjectId, runFilterId)
    ),
    selectMany<EvidenceItemRow>(
      evidenceItemQuery(client, auditProjectId, runFilterId)
    )
  ]);

  const mappedFindings = findings.map(mapFindingRow);
  const summary = asRecord(run?.summary_json);
  const readinessStatus = stringFrom(summary.readinessStatus);
  return {
    auditId: project.id,
    createdAt: project.created_at,
    fileName: project.file_name,
    parseErrors: Array.isArray(project.parse_errors) ? project.parse_errors : [],
    dataset: datasetFromDb(project.dataset_json, normalizedEvents, evidenceItems),
    findings: mappedFindings,
    readinessGate: {
      passed: readinessStatus === "ready",
      blockers: readinessStatus === "ready" ? [] : readinessBlockers(mappedFindings, run?.status ?? project.status, readinessStatus)
    },
    coverage: coverageFromRun(run, mappedFindings),
    mode: project.mode === "customer_facing" ? "customer_facing" : "draft"
  };
}

export interface ObligationExplanation {
  obligationId: string;
  sectionRef?: string;
  plainRequirement: string;
  whyItMatters: string;
  supportText?: string;
  sourceUrl?: string;
  status: string;
}

export async function loadObligationExplanations(obligationIds: string[]): Promise<Record<string, ObligationExplanation>> {
  const ids = [...new Set(obligationIds.filter(Boolean))];
  if (!ids.length) return {};
  const client = createSupabaseAdminClient();
  const rows = await selectMany<{
    obligation_id: string;
    section_ref: string | null;
    plain_requirement: string;
    why_it_matters: string;
    support_text: string | null;
    source_url: string | null;
    status: string;
  }>(
    client
      .from("obligation_explanations")
      .select("obligation_id, section_ref, plain_requirement, why_it_matters, support_text, source_url, status")
      .in("obligation_id", ids)
  );
  const map: Record<string, ObligationExplanation> = {};
  for (const row of rows) {
    map[row.obligation_id] = {
      obligationId: row.obligation_id,
      sectionRef: row.section_ref ?? undefined,
      plainRequirement: row.plain_requirement,
      whyItMatters: row.why_it_matters,
      supportText: row.support_text ?? undefined,
      sourceUrl: row.source_url ?? undefined,
      status: row.status
    };
  }
  return map;
}

export async function loadOperatorAuditArtifact(
  auditProjectId: string,
  artifactTypes: string[],
  session: TraceReadySession
): Promise<OperatorAuditArtifact | undefined> {
  const client = createSupabaseAdminClient();
  const project = await loadAuthorizedProject(client, auditProjectId, session);
  if (!project) return undefined;

  const artifacts = await selectMany<ArtifactRow>(
    client
      .from("audit_artifacts")
      .select("id, artifact_type, file_name, content_type, storage_bucket, storage_key, status, created_at")
      .eq("audit_project_id", auditProjectId)
      .in("artifact_type", artifactTypes)
      .eq("status", "available")
      .order("created_at", { ascending: false })
  );
  const artifact = artifacts.find((item) => artifactTypes.includes(item.artifact_type));
  if (!artifact) return undefined;

  const { data, error } = await client.storage.from(artifact.storage_bucket).download(artifact.storage_key);
  if (error || !data) {
    throw new Error(error?.message ?? "Artifact download failed.");
  }
  return {
    body: new Uint8Array(await data.arrayBuffer()),
    fileName: artifact.file_name,
    contentType: artifact.content_type
  };
}

function findingQuery(client: ReturnType<typeof createSupabaseAdminClient>, auditProjectId: string, auditRunId?: string) {
  const query = client
    .from("audit_findings")
    .select("id, title, status, severity, finding_type, event_id, event_line_id, field_or_kde, observed_value, expected_or_required, recommendation, rule_card_id, rule_card_version, approved_record_id, approved_obligation_id, source_chunk_id, kde_requirement_id, rule_package_id, rule_package_version, check_code, evidence_refs_json, metadata_json, review_state, created_at")
    .eq("audit_project_id", auditProjectId)
    .order("created_at", { ascending: true });
  return auditRunId ? query.eq("audit_run_id", auditRunId) : query;
}

function normalizedEventQuery(client: ReturnType<typeof createSupabaseAdminClient>, auditProjectId: string, auditRunId?: string) {
  const query = client
    .from("normalized_events")
    .select("id, source_row_key, event_type_claim, event_datetime, event_datetime_raw, actor_object_id, from_object_id, to_object_id, document_object_id, classified_ctes_json")
    .eq("audit_project_id", auditProjectId)
    .order("created_at", { ascending: true })
    .limit(500);
  return auditRunId ? query.eq("audit_run_id", auditRunId) : query;
}

function evidenceItemQuery(client: ReturnType<typeof createSupabaseAdminClient>, auditProjectId: string, auditRunId?: string) {
  const query = client
    .from("evidence_items")
    .select("id, evidence_type, canonical_field, source_sheet, source_row_number, source_column, raw_value, normalized_value, review_status, metadata_json")
    .eq("audit_project_id", auditProjectId)
    .order("created_at", { ascending: true })
    .limit(1000);
  return auditRunId ? query.eq("audit_run_id", auditRunId) : query;
}

async function listAccessibleProjects(client: ReturnType<typeof createSupabaseAdminClient>, session: TraceReadySession, limit: number) {
  if (session.role === "founder_admin") {
    return selectMany<ProjectRow>(
      client.from("audit_projects").select(projectSelect).order("created_at", { ascending: false }).limit(limit)
    );
  }

  const memberships = await selectMany<{ customer_id: string }>(
    client.from("customer_memberships").select("customer_id").eq("user_id", session.userId).eq("status", "active")
  );
  const customerIds = [...new Set(memberships.map((membership) => membership.customer_id))];
  const [owned, customerProjects] = await Promise.all([
    selectMany<ProjectRow>(
      client
        .from("audit_projects")
        .select(projectSelect)
        .eq("created_by_user_id", session.userId)
        .order("created_at", { ascending: false })
        .limit(limit)
    ),
    customerIds.length
      ? selectMany<ProjectRow>(
          client
            .from("audit_projects")
            .select(projectSelect)
            .in("customer_id", customerIds)
            .order("created_at", { ascending: false })
            .limit(limit)
        )
      : Promise.resolve([])
  ]);
  return [...new Map([...owned, ...customerProjects].map((project) => [project.id, project])).values()]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .slice(0, limit);
}

async function loadAuthorizedProject(client: ReturnType<typeof createSupabaseAdminClient>, auditProjectId: string, session: TraceReadySession) {
  const project = await selectMaybe<ProjectRow>(
    client.from("audit_projects").select(projectSelect).eq("id", auditProjectId).maybeSingle()
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

function latestByProject<T extends { audit_project_id: string; created_at: string }>(rows: T[]) {
  const byProject = new Map<string, T>();
  for (const row of rows) {
    const current = byProject.get(row.audit_project_id);
    if (!current || row.created_at > current.created_at) byProject.set(row.audit_project_id, row);
  }
  return byProject;
}

function countFindings(rows: Array<{ audit_project_id: string; status: string; severity: string }>) {
  const counts = new Map<string, { findings: number; blockers: number }>();
  for (const row of rows) {
    const current = counts.get(row.audit_project_id) ?? { findings: 0, blockers: 0 };
    if (!["pass", "not_applicable"].includes(row.status)) {
      current.findings += 1;
      if (["critical", "high"].includes(row.severity)) current.blockers += 1;
    }
    counts.set(row.audit_project_id, current);
  }
  return counts;
}

export function mapFindingRow(row: FindingRow): Finding {
  const metadata = asRecord(row.metadata_json);
  const citation = asRecord(metadata.sourceCitation);
  return {
    findingId: row.id,
    title: row.title,
    status: toFindingState(row.status),
    severity: toFindingSeverity(row.severity),
    findingType: row.finding_type,
    eventId: row.event_id ?? undefined,
    eventLineId: row.event_line_id ?? undefined,
    fieldOrKde: row.field_or_kde ?? undefined,
    observedValue: row.observed_value ?? undefined,
    expectedOrRequired: row.expected_or_required ?? undefined,
    recommendation: row.recommendation,
    ruleCardId: row.rule_card_id ?? row.approved_record_id ?? row.approved_obligation_id ?? row.check_code ?? "approved-rule",
    ruleCardVersion: row.rule_card_version ?? row.rule_package_version ?? 1,
    sourceChunkId: row.source_chunk_id ?? stringFrom(citation.chunkId) ?? stringFrom(citation.section) ?? "approved-source",
    kdeRequirementId: row.kde_requirement_id ?? undefined,
    approvedObligationId: row.approved_obligation_id ?? undefined,
    evidenceRefs: evidenceRefsFromJson(row.evidence_refs_json),
    reviewState: toReviewState(row.review_state)
  };
}

function datasetFromDb(datasetJson: unknown, events: NormalizedEventRow[], evidenceItems: EvidenceItemRow[]): NormalizedAuditDataset {
  const existing = asDataset(datasetJson);
  if (existing) return existing;
  return {
    businessProfiles: [],
    exemptionClaims: [],
    products: [],
    productScopeDecisions: [],
    traceabilityPlans: [],
    events: events.map((event) => ({
      eventId: event.id,
      eventType: cteFromEvent(event),
      eventDatetime: event.event_datetime ?? event.event_datetime_raw ?? undefined,
      actorLocationId: event.actor_object_id ?? undefined,
      fromPartnerId: event.from_object_id ?? undefined,
      toPartnerId: event.to_object_id ?? undefined,
      referenceRecordNo: event.document_object_id ?? event.source_row_key,
      eventStatus: "normalized"
    })),
    lineItems: [],
    kdeValues: [],
    lineage: [],
    sourceDocuments: evidenceItems
      .filter((item) => item.evidence_type.toLowerCase().includes("document"))
      .map((item) => ({
        evidenceId: item.id,
        evidenceType: item.evidence_type,
        referenceNo: item.normalized_value ?? item.raw_value ?? item.canonical_field ?? undefined,
        evidenceStatus: item.review_status === "rejected" ? "unverified" : "available"
      }))
  };
}

function readinessStatusFromRun(run?: RunRow) {
  const summary = asRecord(run?.summary_json);
  return stringFrom(summary.readinessStatus) ?? (run?.status === "succeeded" ? "ready" : run?.status);
}

function readinessBlockers(findings: Finding[], runStatus: string, readinessStatus?: string) {
  if (readinessStatus === "blocked" || readinessStatus === "needs_review") {
    return findings.length ? findings.map((finding) => finding.findingId) : [`readiness status: ${readinessStatus}`];
  }
  if (runStatus === "queued" || runStatus === "running") return [`audit run is ${runStatus}`];
  if (runStatus === "failed") return ["audit run failed"];
  return findings.filter((finding) => !["pass", "not_applicable"].includes(finding.status)).map((finding) => finding.findingId);
}

function coverageFromRun(run: RunRow | undefined, findings: Finding[]) {
  const summary = asRecord(run?.summary_json);
  return [
    {
      area: "Parser",
      status: run?.parser_version ? "ready" : run?.status === "queued" ? "queued" : "pending",
      reason: run?.parser_version ?? "Customer workbook parser has not completed."
    },
    {
      area: "Approved rule execution",
      status: run?.status === "succeeded" ? "ready" : run?.status ?? "pending",
      reason: stringFrom(summary.executionVersion) ?? "Waiting for deterministic approved-rule execution."
    },
    {
      area: "Findings",
      status: findings.length ? "review" : run?.status === "succeeded" ? "ready" : "pending",
      reason: findings.length ? `${findings.length} finding(s) require review.` : "No findings persisted for this run."
    }
  ];
}

function cteFromEvent(event: NormalizedEventRow): CTEType {
  const classified = Array.isArray(event.classified_ctes_json) ? event.classified_ctes_json : [];
  const candidate = typeof classified[0] === "string" ? classified[0] : event.event_type_claim;
  if (isCteType(candidate)) return candidate;
  return "shipping";
}

function evidenceRefsFromJson(value: unknown): EvidenceRef[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (typeof item === "string") return { evidenceId: item };
    const record = asRecord(item);
    return {
      evidenceId: stringFrom(record.evidenceId) ?? stringFrom(record.evidence_id),
      sheet: stringFrom(record.sheet),
      row: numberFrom(record.row),
      field: stringFrom(record.field),
      sourceValue: stringFrom(record.sourceValue) ?? stringFrom(record.source_value)
    };
  });
}

function asDataset(value: unknown): NormalizedAuditDataset | undefined {
  const record = asRecord(value);
  return Array.isArray(record.events) && Array.isArray(record.sourceDocuments) ? (record as unknown as NormalizedAuditDataset) : undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function stringFrom(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function numberFrom(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function toFindingState(value: string): FindingState {
  return isFindingState(value) ? value : "not_determined";
}

function toFindingSeverity(value: string): FindingSeverity {
  return value === "low" || value === "medium" || value === "high" || value === "critical" ? value : "medium";
}

function toReviewState(value: string): Finding["reviewState"] {
  return value === "approved" || value === "edited" || value === "dismissed" || value === "needs_more_evidence" ? value : "pending";
}

function isFindingState(value: string): value is FindingState {
  return [
    "pass",
    "gap",
    "conflict",
    "missing_evidence",
    "not_applicable",
    "not_determined",
    "cannot_determine",
    "needs_expert_review",
    "proposed_change",
    "operational_anomaly"
  ].includes(value);
}

function isCteType(value: unknown): value is CTEType {
  return (
    value === "harvest" ||
    value === "cooling" ||
    value === "initial_packing" ||
    value === "first_land_based_receiving" ||
    value === "shipping" ||
    value === "receiving" ||
    value === "transformation"
  );
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
