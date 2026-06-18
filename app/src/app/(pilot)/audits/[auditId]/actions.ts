"use server";

import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadAuditProcessingStatus, type AuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

export type AuditAdvanceState = { state: "ready" | "processing" | "failed"; message?: string };

const RUNNABLE_JOB_STATES = ["queued", "retryable", "running"];

// Drives a customer audit forward without a cron/queue worker: the audit page polls this while
// the spinner is showing. It pushes the Python worker (parse + rule execution run synchronously
// in one slice) and reports whether the audit is ready, still processing, or failed.
export async function advanceAuditProcessing(auditId: string): Promise<AuditAdvanceState> {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}`)) {
    return { state: "failed", message: "You are not authorized to view this audit." };
  }

  let status = await loadAuditProcessingStatus(auditId, session).catch(() => undefined);
  if (!status) return { state: "failed", message: "This audit could not be found." };
  if (isReady(status)) return { state: "ready" };

  if (status.job && RUNNABLE_JOB_STATES.includes(status.job.status)) {
    await triggerWorkerSlice(session.userId);
    status = (await loadAuditProcessingStatus(auditId, session).catch(() => status)) ?? status;
  }

  if (isReady(status)) return { state: "ready" };
  if (status.job?.status === "failed" && !status.job.retryable) {
    return { state: "failed", message: jobErrorMessage(status) };
  }
  return { state: "processing" };
}

// "Try again" after a failure: re-queue the latest job and push the worker once more.
export async function retryAuditProcessing(auditId: string): Promise<AuditAdvanceState> {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}`)) {
    return { state: "failed", message: "You are not authorized to view this audit." };
  }
  const status = await loadAuditProcessingStatus(auditId, session).catch(() => undefined);
  if (!status) return { state: "failed", message: "This audit could not be found." };
  if (isReady(status)) return { state: "ready" };

  if (status.job && ["failed", "retryable"].includes(status.job.status)) {
    const client = createSupabaseAdminClient();
    const { error } = await client
      .from("audit_jobs")
      .update({ status: "retryable", failure_category: null, error_json: null, locked_by: null, locked_at: null, available_at: new Date().toISOString() })
      .eq("id", status.job.id)
      .eq("audit_project_id", auditId)
      .in("status", ["failed", "retryable"]);
    if (error) return { state: "failed", message: error.message };
  }
  return advanceAuditProcessing(auditId);
}

function isReady(status: AuditProcessingStatus): boolean {
  return status.projectStatus === "succeeded" || status.run?.status === "succeeded";
}

function jobErrorMessage(status: AuditProcessingStatus): string {
  const category = status.job?.failureCategory;
  return category ? `The audit could not be completed (${category}).` : "The audit could not be completed.";
}

async function triggerWorkerSlice(userId: string): Promise<void> {
  const pythonApiUrl = (process.env.TRACEREADY_PYTHON_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/u, "");
  const internalToken = process.env.TRACEREADY_INTERNAL_API_TOKEN;
  if (!internalToken) return;
  try {
    await fetch(`${pythonApiUrl}/internal/jobs/audit/process-slice`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-traceready-internal-token": internalToken },
      body: JSON.stringify({
        worker_id: `next-audit-${userId}`,
        job_types: ["parse_customer_workbook", "execute_approved_rules"],
        max_jobs: 2,
        stale_lock_minutes: 15
      }),
      cache: "no-store"
    });
  } catch {
    // Swallow — the poll will retry on the next tick.
  }
}
