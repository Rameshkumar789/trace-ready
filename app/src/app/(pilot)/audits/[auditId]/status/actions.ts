"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadAuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

export async function processAuditJobSliceAction(formData: FormData) {
  const auditId = requiredText(formData, "auditId");
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/status`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}/status`)}`);
  }
  const status = await loadAuditProcessingStatus(auditId, session);
  if (!status?.job || !["queued", "retryable", "running"].includes(status.job.status)) {
    redirect(`/audits/${auditId}/status?worker=${encodeURIComponent("No queued or retryable Python job is available for this audit.")}`);
  }

  const pythonApiUrl = (process.env.TRACEREADY_PYTHON_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/u, "");
  const internalToken = process.env.TRACEREADY_INTERNAL_API_TOKEN;
  if (!internalToken) {
    redirect(`/audits/${auditId}/status?worker=${encodeURIComponent("TRACEREADY_INTERNAL_API_TOKEN is missing in the Next.js app environment.")}`);
  }

  try {
    const response = await fetch(`${pythonApiUrl}/internal/jobs/audit/process-slice`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-traceready-internal-token": internalToken
      },
      body: JSON.stringify({
        worker_id: `next-local-${session.userId}`,
        job_types: ["parse_customer_workbook", "execute_approved_rules"],
        max_jobs: 2,
        stale_lock_minutes: 15
      }),
      cache: "no-store"
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${text}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Python worker request failed.";
    redirect(`/audits/${auditId}/status?worker=${encodeURIComponent(message)}`);
  }

  revalidatePath(`/audits/${auditId}/status`);
  redirect(`/audits/${auditId}/status?worker=${encodeURIComponent("Python worker slice requested.")}`);
}

export async function retryAuditJobAction(formData: FormData) {
  const auditId = requiredText(formData, "auditId");
  const jobId = requiredText(formData, "jobId");
  const reason = requiredText(formData, "reason");
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/status`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}/status`)}`);
  }
  const status = await loadAuditProcessingStatus(auditId, session);
  if (!status?.job || status.job.id !== jobId || !status.job.retryable) {
    throw new Error("Job is not retryable or is not accessible.");
  }
  const client = createSupabaseAdminClient();
  const existing = await client.from("audit_jobs").select("checkpoint_json").eq("id", jobId).maybeSingle();
  if (existing.error) throw new Error(existing.error.message);
  const checkpoint = existing.data?.checkpoint_json && typeof existing.data.checkpoint_json === "object" && !Array.isArray(existing.data.checkpoint_json)
    ? existing.data.checkpoint_json
    : {};
  const { error } = await client
    .from("audit_jobs")
    .update({
      status: "retryable",
      failure_category: null,
      error_json: null,
      locked_by: null,
      locked_at: null,
      available_at: new Date().toISOString(),
      checkpoint_json: {
        ...checkpoint,
        manualRetry: {
          requestedBy: session.email,
          reason,
          requestedAt: new Date().toISOString()
        }
      }
    })
    .eq("id", jobId)
    .eq("audit_project_id", auditId)
    .in("status", ["failed", "retryable"]);
  if (error) throw new Error(error.message);
  const event = await client.from("audit_job_events").insert({
    audit_job_id: jobId,
    audit_project_id: auditId,
    event_type: "manual_retry_requested",
    message: "Manual retry requested from audit status page.",
    payload_json: {
      requestedBy: session.email,
      reason
    }
  });
  if (event.error) throw new Error(event.error.message);
  revalidatePath(`/audits/${auditId}/status`);
  redirect(`/audits/${auditId}/status`);
}

function requiredText(formData: FormData, key: string) {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) throw new Error(`${key} is required.`);
  return value.trim();
}
