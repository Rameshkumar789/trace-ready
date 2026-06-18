"use server";

import { redirect } from "next/navigation";
import { createUploadAuditJob } from "@/lib/audit/upload-job";
import { validateUploadMetadata } from "@/lib/security/upload-security";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";

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

  // Run parsing + deterministic rule execution synchronously so the operator sees results
  // immediately. The worker slice claims both the parse and execute jobs in one call. We then
  // go straight to the audit workspace, which shows a spinner and finishes processing itself if
  // this call did not complete in time (no separate status page).
  await requestPythonWorkerSlice(session.userId).catch((error) => {
    console.error("Failed to trigger Python worker", error);
  });

  redirect(`/audits/${queued.auditProjectId}`);
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
}
