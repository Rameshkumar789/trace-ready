"use server";

import { redirect } from "next/navigation";
import { createUploadAuditJob } from "@/lib/audit/upload-job";
import { loadAuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { validateUploadMetadata } from "@/lib/security/upload-security";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import type { TraceReadySession } from "@/lib/auth/session-cookie";

export async function uploadWorkbookAction(formData: FormData) {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, "/upload")) {
    redirect("/login/operator?auth=required&next=/upload");
  }

  const file = formData.get("workbook");
  if (!(file instanceof File)) {
    redirect("/upload?error=missing_file");
  }

  const uploadValidation = validateUploadMetadata(file.name, file.size);
  if (!uploadValidation.valid) {
    redirect(`/upload?error=${encodeURIComponent(uploadValidation.errors.join("; "))}`);
  }

  const bytes = new Uint8Array(await file.arrayBuffer());
  let queued;
  try {
    queued = await createUploadAuditJob({
      fileName: file.name,
      bytes,
      contentType: file.type || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      session
    });
  } catch (error) {
    console.error("Failed to queue workbook upload", error);
    redirect(`/upload?error=${encodeURIComponent("Upload could not be queued. Check Supabase configuration and try again.")}`);
  }

  // Run parsing + deterministic rule execution synchronously so the operator sees
  // results immediately instead of a queue/processing screen. The worker slice claims
  // both the parse and execute jobs in one call.
  const workerMessage = await requestPythonWorkerSlice(session.userId).catch((error) => {
    console.error("Failed to trigger Python worker", error);
    return error instanceof Error ? `Upload queued, but the audit could not be run automatically: ${error.message}` : "Upload queued, but the audit could not be run automatically.";
  });

  // If processing completed, go straight to the results workspace; otherwise fall back
  // to the status page so the operator can see progress / retry.
  if (await auditProcessingFinished(queued.auditProjectId, session)) {
    redirect(`/audits/${queued.auditProjectId}`);
  }
  redirect(`/audits/${queued.auditProjectId}/status?worker=${encodeURIComponent(workerMessage)}`);
}

async function auditProcessingFinished(auditProjectId: string, session: TraceReadySession): Promise<boolean> {
  try {
    const status = await loadAuditProcessingStatus(auditProjectId, session);
    return status?.projectStatus === "succeeded" || status?.run?.status === "succeeded";
  } catch (error) {
    console.error("Failed to read audit status after upload", error);
    return false;
  }
}

async function requestPythonWorkerSlice(userId: string) {
  const pythonApiUrl = (process.env.TRACEREADY_PYTHON_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/u, "");
  const internalToken = process.env.TRACEREADY_INTERNAL_API_TOKEN;
  if (!internalToken) {
    throw new Error("TRACEREADY_INTERNAL_API_TOKEN is missing in the Next.js app environment.");
  }
  const response = await fetch(`${pythonApiUrl}/internal/jobs/audit/process-slice`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-traceready-internal-token": internalToken
    },
    body: JSON.stringify({
      worker_id: `next-upload-${userId}`,
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
  const result = await response.json().catch(() => undefined);
  const processedCount = typeof result?.processedCount === "number" ? result.processedCount : 0;
  return processedCount > 0 ? `Python worker processed ${processedCount} job slice${processedCount === 1 ? "" : "s"}.` : "Python worker was called, but no queued jobs were claimed.";
}
