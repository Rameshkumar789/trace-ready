import { createSupabaseAdminClient } from "@/lib/supabase/admin";

export interface RegulatorySourceRow {
  id: string;
  title: string;
  source_type: string;
  source_status: string;
  authority_rank: string;
  url: string;
  citation: string;
  published_date: string | null;
  effective_date: string | null;
  compliance_date: string | null;
  is_finalized: boolean;
  retrieved_at: string;
  text_hash: string;
  summary: string | null;
  chunkCount?: number;
}

export interface SourceChunkRow {
  id: string;
  regulatory_source_id: string;
  chunk_code: string;
  section_label: string;
  source_location: string;
  section_ref: string | null;
  page_number: number | null;
  text: string;
  summary: string;
  citation: string;
  text_hash: string;
  authority_rank: string | null;
  status: string;
}

export interface DraftRecordRow {
  id: string;
  collection: string;
  record_id: string;
  source_phase: string;
  extraction_method: string;
  confidence: string;
  review_status: string;
  source_chunk_ids: unknown;
  citation_count: number;
  citation_coverage_status: string;
  schema_valid: boolean;
  citation_valid: boolean;
  validation_errors: unknown;
  reviewer_blockers: unknown;
  payload?: unknown;
  updated_at?: string;
}

export interface RuleCardRow {
  id: string;
  rule_code: string;
  title: string;
  rule_area: string;
  cte_type: string | null;
  status: string;
  is_finalized_source: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  version: number;
}

export interface KdeRequirementRow {
  id: string;
  cte_type: string;
  kde_name: string;
  field_key: string;
  required_status: string;
  source_chunk_id: string;
  rule_card_id: string;
  severity_if_missing: string;
  status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  version: number;
}

export interface ScenarioCaseRow {
  id: string;
  name: string;
  scenario_group: string;
  expected_status: string;
  requires_expert_review: boolean;
  status: string;
}

export interface ScenarioRegressionRunRow {
  id: string;
  approved_rule_package_id: string | null;
  run_type: string;
  status: string;
  benchmark_count: number;
  pass_count: number;
  fail_count: number;
  result_hash: string | null;
  created_at: string;
}

export interface ApprovedRulePackageRow {
  id: string;
  package_id: string;
  version: number;
  status: string;
  package_hash: string;
  approved_at: string;
  approved_by: string;
  approval_role: string;
  scenario_gate_status: string | null;
}

export interface ReviewerDashboardSummary {
  regulatoryDrafts: number;
  readyForReview: number;
  rejectedRecords: number;
  approvedRecords: number;
  sourceChunks: number;
  approvedPackages: number;
  customerReviewQueue: number;
  customerReviewActions: number;
  latestScenarioRun?: ScenarioRegressionRunRow;
}

export interface CustomerFindingReviewRow {
  id: string;
  audit_project_id: string;
  audit_run_id: string | null;
  title: string;
  status: string;
  severity: string;
  finding_type: string;
  field_or_kde: string | null;
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
  metadata_json: unknown;
  review_state: string;
  created_at: string;
}

export interface ReviewerQueueItem {
  id: string;
  objectId: string;
  objectType: "regulatory_draft" | "customer_finding";
  label: string;
  subtitle: string;
  priority: "high" | "medium" | "low";
  citation: string;
  status: string;
  owner: string;
  updatedAt: string;
  sourceChunkIds: string[];
  targetHref: string;
  canApproveDraft: boolean;
  blockers: string[];
  evidence?: ReviewerEvidenceSnapshot;
}

export interface ReviewerEvidenceSnapshot {
  chunkId: string;
  chunkCode: string;
  sourceId: string;
  sourceTitle: string;
  sectionLabel: string;
  sourceLocation: string;
  citation: string;
  text: string;
  summary: string;
  sourceUrl: string;
  sourceDate: string | null;
  retrievedAt: string | null;
  authorityRank: string | null;
  sourceStatus: string | null;
}

export interface ReviewerWorkbenchData {
  summary: ReviewerDashboardSummary;
  queueItems: ReviewerQueueItem[];
  queueTotal: number;
  draftQueueTotal: number;
  findingQueueTotal: number;
  highPriorityTotal: number;
  selectedItem?: ReviewerQueueItem;
  latestPackage?: ApprovedRulePackageRow;
}

export async function listRegulatorySources(limit = 250) {
  const client = createSupabaseAdminClient();
  const [sources, chunks] = await Promise.all([
    selectMany<RegulatorySourceRow>(
      client
        .from("regulatory_sources")
        .select("id, title, source_type, source_status, authority_rank, url, citation, published_date, effective_date, compliance_date, is_finalized, retrieved_at, text_hash, summary")
        .order("authority_rank", { ascending: true })
        .limit(limit)
    ),
    selectMany<{ regulatory_source_id: string }>(
      client.from("source_chunks").select("regulatory_source_id").limit(5000)
    )
  ]);
  const counts = new Map<string, number>();
  for (const chunk of chunks) counts.set(chunk.regulatory_source_id, (counts.get(chunk.regulatory_source_id) ?? 0) + 1);
  return sources.map((source) => ({ ...source, chunkCount: counts.get(source.id) ?? 0 }));
}

export async function loadRegulatorySourceDetail(sourceId: string) {
  const client = createSupabaseAdminClient();
  const [source, chunks] = await Promise.all([
    selectMaybe<RegulatorySourceRow>(
      client
        .from("regulatory_sources")
        .select("id, title, source_type, source_status, authority_rank, url, citation, published_date, effective_date, compliance_date, is_finalized, retrieved_at, text_hash, summary")
        .eq("id", sourceId)
        .maybeSingle()
    ),
    selectMany<SourceChunkRow>(
      client
        .from("source_chunks")
        .select("id, regulatory_source_id, chunk_code, section_label, source_location, section_ref, page_number, text, summary, citation, text_hash, authority_rank, status")
        .eq("regulatory_source_id", sourceId)
        .order("chunk_code", { ascending: true })
        .limit(500)
    )
  ]);
  return source ? { source, chunks } : undefined;
}

export async function listSourceChunks(limit = 500) {
  return selectMany<SourceChunkRow>(
    createSupabaseAdminClient()
      .from("source_chunks")
      .select("id, regulatory_source_id, chunk_code, section_label, source_location, section_ref, page_number, text, summary, citation, text_hash, authority_rank, status")
      .order("citation", { ascending: true })
      .limit(limit)
  );
}

export async function listDraftRecords(limit = 250) {
  return selectMany<DraftRecordRow>(
    createSupabaseAdminClient()
      .from("regulatory_draft_records")
      .select("id, collection, record_id, source_phase, extraction_method, confidence, review_status, source_chunk_ids, citation_count, citation_coverage_status, schema_valid, citation_valid, validation_errors, reviewer_blockers, payload, updated_at")
      .order("updated_at", { ascending: false })
      .limit(limit)
  );
}

export async function listDraftRecordsPage({
  page,
  pageSize,
  reviewStatus
}: {
  page: number;
  pageSize: number;
  reviewStatus?: string;
}) {
  const from = Math.max(0, page - 1) * pageSize;
  const to = from + pageSize - 1;
  let query = createSupabaseAdminClient()
    .from("regulatory_draft_records")
    .select("id, collection, record_id, source_phase, extraction_method, confidence, review_status, source_chunk_ids, citation_count, citation_coverage_status, schema_valid, citation_valid, validation_errors, reviewer_blockers, payload, updated_at", { count: "exact" })
    .order("updated_at", { ascending: false })
    .range(from, to);
  if (reviewStatus) query = query.eq("review_status", reviewStatus);
  const { data, error, count } = await query;
  if (error) throw new Error(error.message);
  return {
    rows: (data as DraftRecordRow[] | null) ?? [],
    total: count ?? 0
  };
}

export async function countReadyDraftRecords() {
  const { error, count } = await createSupabaseAdminClient()
    .from("regulatory_draft_records")
    .select("id", { count: "exact", head: true })
    .eq("review_status", "needs_review")
    .eq("schema_valid", true)
    .eq("citation_valid", true);
  if (error) throw new Error(error.message);
  return count ?? 0;
}

export async function loadDraftRecord(draftId: string) {
  return selectMaybe<DraftRecordRow>(
    createSupabaseAdminClient()
      .from("regulatory_draft_records")
      .select("id, collection, record_id, source_phase, extraction_method, confidence, review_status, source_chunk_ids, citation_count, citation_coverage_status, schema_valid, citation_valid, validation_errors, reviewer_blockers, payload, updated_at")
      .eq("id", draftId)
      .maybeSingle()
  );
}

export async function listRuleCards(limit = 500) {
  return selectMany<RuleCardRow>(
    createSupabaseAdminClient()
      .from("rule_cards")
      .select("id, rule_code, title, rule_area, cte_type, status, is_finalized_source, reviewed_by, reviewed_at, version")
      .order("rule_code", { ascending: true })
      .limit(limit)
  );
}

export async function listKdeRequirements(limit = 500) {
  return selectMany<KdeRequirementRow>(
    createSupabaseAdminClient()
      .from("kde_requirements")
      .select("id, cte_type, kde_name, field_key, required_status, source_chunk_id, rule_card_id, severity_if_missing, status, reviewed_by, reviewed_at, version")
      .order("cte_type", { ascending: true })
      .limit(limit)
  );
}

export async function listScenarioCases(limit = 500) {
  return selectMany<ScenarioCaseRow>(
    createSupabaseAdminClient()
      .from("scenario_cases")
      .select("id, name, scenario_group, expected_status, requires_expert_review, status")
      .order("scenario_group", { ascending: true })
      .limit(limit)
  );
}

export async function listScenarioRegressionRuns(limit = 25) {
  return selectMany<ScenarioRegressionRunRow>(
    createSupabaseAdminClient()
      .from("scenario_regression_runs")
      .select("id, approved_rule_package_id, run_type, status, benchmark_count, pass_count, fail_count, result_hash, created_at")
      .order("created_at", { ascending: false })
      .limit(limit)
  );
}

export async function listApprovedRulePackages(limit = 50) {
  return selectMany<ApprovedRulePackageRow>(
    createSupabaseAdminClient()
      .from("approved_rule_packages")
      .select("id, package_id, version, status, package_hash, approved_at, approved_by, approval_role, scenario_gate_status")
      .order("approved_at", { ascending: false })
      .limit(limit)
  );
}

export async function loadRegulatoryCoverageSummary() {
  const [drafts, approvedPackages, scenarios, runs] = await Promise.all([
    listDraftRecords(5000),
    listApprovedRulePackages(100),
    listScenarioCases(5000),
    listScenarioRegressionRuns(25)
  ]);
  const statusCounts = countBy(drafts, (draft) => draft.review_status);
  const readyForReview = drafts.filter((draft) => draft.review_status === "needs_review" && draft.schema_valid && draft.citation_valid).length;
  const rejectedRecords = drafts.filter((draft) => draft.review_status === "rejected").length;
  const approvedRecords = drafts.filter((draft) => draft.review_status === "approved").length;
  const latestRun = runs[0];
  return {
    draftRecords: drafts.length,
    readyForReview,
    rejectedRecords,
    approvedRecords,
    statusCounts,
    approvedPackages: approvedPackages.length,
    scenarioCases: scenarios.length,
    latestScenarioRun: latestRun
  };
}

export async function loadReviewerDashboardSummary(): Promise<ReviewerDashboardSummary> {
  const client = createSupabaseAdminClient();
  const [coverage, sourceChunks, customerFindings, customerActions] = await Promise.all([
    loadRegulatoryCoverageSummary(),
    selectMany<{ id: string }>(client.from("source_chunks").select("id").limit(5000)),
    selectMany<{ id: string; status: string; review_state: string }>(
      client.from("audit_findings").select("id, status, review_state").limit(5000)
    ),
    selectMany<{ id: string }>(client.from("customer_review_actions").select("id").limit(5000))
  ]);
  return {
    regulatoryDrafts: coverage.draftRecords,
    readyForReview: coverage.readyForReview,
    rejectedRecords: coverage.rejectedRecords,
    approvedRecords: coverage.approvedRecords,
    sourceChunks: sourceChunks.length,
    approvedPackages: coverage.approvedPackages,
    customerReviewQueue: countCustomerReviewQueue(customerFindings),
    customerReviewActions: customerActions.length,
    latestScenarioRun: coverage.latestScenarioRun
  };
}

export async function loadReviewerWorkbenchData(limit = 100): Promise<ReviewerWorkbenchData> {
  const client = createSupabaseAdminClient();
  const [summary, drafts, findings, chunks, sources, packages] = await Promise.all([
    loadReviewerDashboardSummary(),
    listDraftRecords(1000),
    selectMany<CustomerFindingReviewRow>(
      client
        .from("audit_findings")
        .select("id, audit_project_id, audit_run_id, title, status, severity, finding_type, field_or_kde, recommendation, rule_card_id, rule_card_version, approved_record_id, approved_obligation_id, source_chunk_id, kde_requirement_id, rule_package_id, rule_package_version, check_code, metadata_json, review_state, created_at")
        .order("created_at", { ascending: false })
        .limit(1000)
    ),
    listSourceChunks(5000),
    listRegulatorySources(500),
    listApprovedRulePackages(10)
  ]);
  const chunkIndex = new Map(chunks.map((chunk) => [chunk.id, chunk]));
  const sourceIndex = new Map(sources.map((source) => [source.id, source]));
  const sourceEvidence = (chunkIds: string[]) => {
    const chunk = chunkIds.map((chunkId) => chunkIndex.get(chunkId)).find((candidate): candidate is SourceChunkRow => Boolean(candidate));
    if (!chunk) return undefined;
    const source = sourceIndex.get(chunk.regulatory_source_id);
    return {
      chunkId: chunk.id,
      chunkCode: chunk.chunk_code,
      sourceId: chunk.regulatory_source_id,
      sourceTitle: source?.title ?? chunk.regulatory_source_id,
      sectionLabel: chunk.section_label,
      sourceLocation: chunk.source_location,
      citation: chunk.citation,
      text: chunk.text,
      summary: chunk.summary,
      sourceUrl: source?.url ?? "",
      sourceDate: source?.published_date ?? source?.effective_date ?? source?.compliance_date ?? null,
      retrievedAt: source?.retrieved_at ?? null,
      authorityRank: chunk.authority_rank ?? source?.authority_rank ?? null,
      sourceStatus: source?.source_status ?? null
    } satisfies ReviewerEvidenceSnapshot;
  };
  const draftItems = drafts
    .filter((draft) => draft.review_status === "needs_review")
    .map((draft) => {
      const chunkIds = sourceChunkIdsFromUnknown(draft.source_chunk_ids);
      const blockers = blockersForDraft(draft);
      const ready = draft.schema_valid && draft.citation_valid && blockers.length === 0;
      const priority = !draft.citation_valid || blockers.length ? "high" : draft.confidence === "low" ? "medium" : "low";
      return {
        id: `draft:${draft.id}`,
        objectId: draft.id,
        objectType: "regulatory_draft",
        label: draftTitle(draft),
        subtitle: "AI-drafted regulatory rule",
        priority,
        citation: sourceEvidence(chunkIds)?.citation ?? `${draft.citation_count} citation${draft.citation_count === 1 ? "" : "s"}`,
        status: ready ? "Pending your review" : "Blocked evidence",
        owner: ready ? "Reviewer" : "System gate",
        updatedAt: draft.updated_at ?? "",
        sourceChunkIds: chunkIds,
        targetHref: "/admin/regulatory/review",
        canApproveDraft: ready,
        blockers,
        evidence: sourceEvidence(chunkIds)
      } satisfies ReviewerQueueItem;
    });
  const findingItems = findings
    .filter((finding) => countCustomerReviewQueue([finding]) > 0)
    .map((finding) => {
      const metadata = asRecord(finding.metadata_json);
      const sourceCitation = asRecord(metadata.sourceCitation);
      const chunkIds = [
        finding.source_chunk_id,
        stringFrom(sourceCitation.chunkId),
        stringFrom(sourceCitation.sourceChunkId)
      ].filter((value): value is string => Boolean(value));
      return {
        id: `finding:${finding.id}`,
        objectId: finding.id,
        objectType: "customer_finding",
        label: finding.title,
        subtitle: humanizeCollection(finding.finding_type),
        priority: findingPriority(finding.severity),
        citation: sourceEvidence(chunkIds)?.citation ?? finding.rule_card_id ?? finding.approved_record_id ?? finding.check_code ?? "Approved rule",
        status: humanizeCollection(finding.review_state),
        owner: "Customer audit",
        updatedAt: finding.created_at,
        sourceChunkIds: chunkIds,
        targetHref: `/audits/${finding.audit_project_id}/review?finding=${encodeURIComponent(finding.id)}`,
        canApproveDraft: false,
        blockers: finding.recommendation ? [finding.recommendation] : [],
        evidence: sourceEvidence(chunkIds)
      } satisfies ReviewerQueueItem;
    });
  const allQueueItems = [...draftItems, ...findingItems].sort(
    (left, right) => priorityRank(left.priority) - priorityRank(right.priority) || right.updatedAt.localeCompare(left.updatedAt)
  );
  const queueItems = allQueueItems.slice(0, limit);
  return {
    summary,
    queueItems,
    queueTotal: allQueueItems.length,
    draftQueueTotal: draftItems.length,
    findingQueueTotal: findingItems.length,
    highPriorityTotal: allQueueItems.filter((item) => item.priority === "high").length,
    selectedItem: queueItems[0],
    latestPackage: packages[0]
  };
}

export function arrayLength(value: unknown) {
  return Array.isArray(value) ? value.length : 0;
}

export function blockersForDraft(draft: DraftRecordRow) {
  const blockers = [...arrayText(draft.reviewer_blockers), ...arrayText(draft.validation_errors)];
  if (!draft.schema_valid) blockers.push("schema invalid");
  if (!draft.citation_valid) blockers.push("citation invalid");
  return [...new Set(blockers)];
}

export function countCustomerReviewQueue(rows: Array<{ status: string; review_state: string }>) {
  return rows.filter((row) => {
    const status = row.status.toLowerCase();
    const reviewState = row.review_state.toLowerCase();
    return !["pass", "not_applicable", "resolved"].includes(status) && !["approved", "dismissed"].includes(reviewState);
  }).length;
}

function arrayText(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function countBy<T>(rows: T[], key: (row: T) => string) {
  return rows.reduce<Record<string, number>>((acc, row) => {
    const value = key(row);
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}

function sourceChunkIdsFromUnknown(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => {
      if (typeof item === "string") return [item];
      const record = asRecord(item);
      return [stringFrom(record.id), stringFrom(record.chunkId), stringFrom(record.source_chunk_id)].filter((candidate): candidate is string => Boolean(candidate));
    });
  }
  if (typeof value === "string") {
    if (!value.trim()) return [];
    try {
      return sourceChunkIdsFromUnknown(JSON.parse(value));
    } catch {
      return [value];
    }
  }
  return [];
}

function draftTitle(draft: DraftRecordRow) {
  const payload = asRecord(draft.payload);
  return (
    stringFrom(payload.title) ??
    stringFrom(payload.ruleTitle) ??
    stringFrom(payload.kdeName) ??
    stringFrom(payload.name) ??
    stringFrom(payload.decisionQuestion) ??
    humanizeDraftId(draft.record_id)
  );
}

function humanizeDraftId(value: string) {
  const withoutPrefixes = value.replace(/^(scenario[_-])+/i, "");
  return humanizeCollection(withoutPrefixes);
}

function humanizeCollection(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function findingPriority(severity: string): ReviewerQueueItem["priority"] {
  const normalized = severity.toLowerCase();
  if (normalized === "critical" || normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  return "low";
}

function priorityRank(priority: ReviewerQueueItem["priority"]) {
  if (priority === "high") return 0;
  if (priority === "medium") return 1;
  return 2;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function stringFrom(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
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
