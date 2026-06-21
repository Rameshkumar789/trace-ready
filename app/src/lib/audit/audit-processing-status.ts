import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import type { BellwetherSession } from "@/lib/auth/session";

export interface AuditProcessingStatus {
  auditProjectId: string;
  fileName: string;
  customerName?: string;
  projectStatus: string;
  createdAt: string;
  updatedAt: string;
  rawWorkbookKey?: string;
  run?: {
    id: string;
    status: string;
    parserVersion?: string;
    classifierVersion?: string;
    rulePackageId?: string;
    rulePackageVersion?: number;
    createdAt: string;
    updatedAt: string;
  };
  file?: {
    id: string;
    status: string;
    storageBucket: string;
    storageKey: string;
    fileHash?: string;
    sizeBytes?: number;
    uploadedAt: string;
  };
  job?: {
    id: string;
    jobType: string;
    status: string;
    attemptCount: number;
    maxAttempts: number;
    failureCategory?: string;
    error?: Record<string, unknown>;
    retryable: boolean;
    createdAt: string;
    updatedAt: string;
  };
  events: Array<{
    id: string;
    eventType: string;
    message?: string;
    payload?: Record<string, unknown>;
    createdAt: string;
  }>;
}

interface ProjectRow {
  id: string;
  customer_id: string | null;
  customer_name: string | null;
  file_name: string;
  status: string;
  created_by_user_id: string | null;
  raw_workbook_key: string | null;
  created_at: string;
  updated_at: string;
}

interface RunRow {
  id: string;
  status: string;
  parser_version: string | null;
  classifier_version: string | null;
  rule_package_id: string | null;
  rule_package_version: number | null;
  created_at: string;
  updated_at: string;
}

interface FileRow {
  id: string;
  status: string;
  storage_bucket: string;
  storage_key: string;
  file_hash: string | null;
  size_bytes: number | null;
  uploaded_at: string;
}

interface JobRow {
  id: string;
  job_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  failure_category: string | null;
  error_json: unknown;
  created_at: string;
  updated_at: string;
}

interface JobEventRow {
  id: string;
  event_type: string;
  message: string | null;
  payload_json: unknown;
  created_at: string;
}

export async function loadAuditProcessingStatus(auditProjectId: string, session: BellwetherSession): Promise<AuditProcessingStatus | undefined> {
  const client = createSupabaseAdminClient();
  const project = await selectMaybe<ProjectRow>(
    client
      .from("audit_projects")
      .select("id, customer_id, customer_name, file_name, status, created_by_user_id, raw_workbook_key, created_at, updated_at")
      .eq("id", auditProjectId)
      .maybeSingle()
  );

  if (!project || !(await canReadProject(project, session))) {
    return undefined;
  }

  const [run, file, job] = await Promise.all([
    selectMaybe<RunRow>(
      client
        .from("audit_runs")
        .select("id, status, parser_version, classifier_version, rule_package_id, rule_package_version, created_at, updated_at")
        .eq("audit_project_id", auditProjectId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    ),
    selectMaybe<FileRow>(
      client
        .from("audit_files")
        .select("id, status, storage_bucket, storage_key, file_hash, size_bytes, uploaded_at")
        .eq("audit_project_id", auditProjectId)
        .order("uploaded_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    ),
    selectMaybe<JobRow>(
      client
        .from("audit_jobs")
        .select("id, job_type, status, attempt_count, max_attempts, failure_category, error_json, created_at, updated_at")
        .eq("audit_project_id", auditProjectId)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    )
  ]);
  const events = job
    ? await selectMany<JobEventRow>(
        client
          .from("audit_job_events")
          .select("id, event_type, message, payload_json, created_at")
          .eq("audit_job_id", job.id)
          .order("created_at", { ascending: false })
          .limit(25)
      )
    : [];

  return {
    auditProjectId: project.id,
    fileName: project.file_name,
    customerName: project.customer_name ?? undefined,
    projectStatus: project.status,
    createdAt: project.created_at,
    updatedAt: project.updated_at,
    rawWorkbookKey: project.raw_workbook_key ?? undefined,
    run: run
      ? {
          id: run.id,
          status: run.status,
          parserVersion: run.parser_version ?? undefined,
          classifierVersion: run.classifier_version ?? undefined,
          rulePackageId: run.rule_package_id ?? undefined,
          rulePackageVersion: run.rule_package_version ?? undefined,
          createdAt: run.created_at,
          updatedAt: run.updated_at
        }
      : undefined,
    file: file
      ? {
          id: file.id,
          status: file.status,
          storageBucket: file.storage_bucket,
          storageKey: file.storage_key,
          fileHash: file.file_hash ?? undefined,
          sizeBytes: file.size_bytes ?? undefined,
          uploadedAt: file.uploaded_at
        }
      : undefined,
    job: job
      ? {
          id: job.id,
          jobType: job.job_type,
          status: job.status,
          attemptCount: job.attempt_count,
          maxAttempts: job.max_attempts,
          failureCategory: job.failure_category ?? undefined,
          error: asRecord(job.error_json),
          retryable: ["failed", "retryable"].includes(job.status) && job.attempt_count < job.max_attempts,
          createdAt: job.created_at,
          updatedAt: job.updated_at
        }
      : undefined,
    events: events.map((event) => ({
      id: event.id,
      eventType: event.event_type,
      message: event.message ?? undefined,
      payload: asRecord(event.payload_json),
      createdAt: event.created_at
    }))
  };

  async function canReadProject(projectRow: ProjectRow, activeSession: BellwetherSession) {
    if (activeSession.role === "founder_admin" || projectRow.created_by_user_id === activeSession.userId) {
      return true;
    }
    if (!projectRow.customer_id) return false;
    const membership = await selectMaybe<{ id: string }>(
      client
        .from("customer_memberships")
        .select("id")
        .eq("customer_id", projectRow.customer_id)
        .eq("user_id", activeSession.userId)
        .eq("status", "active")
        .maybeSingle()
    );
    return Boolean(membership);
  }
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

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}
