import Link from "next/link";
import type React from "react";
import { redirect } from "next/navigation";
import { AlertTriangle, CheckCircle2, ChevronRight, Clock3, FileSpreadsheet, Loader2, ServerCog } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadAuditProcessingStatus } from "@/lib/audit/audit-processing-status";
import { processAuditJobSliceAction, retryAuditJobAction } from "./actions";

export default async function AuditStatusPage({ params, searchParams }: { params: Promise<{ auditId: string }>; searchParams?: Promise<{ worker?: string }> }) {
  const { auditId } = await params;
  const query = await searchParams;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/status`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}/status`)}`);
  }

  let status;
  let loadError: string | undefined;
  try {
    status = await loadAuditProcessingStatus(auditId, session);
  } catch (error) {
    loadError = error instanceof Error ? error.message : "Unable to load audit status.";
  }

  return (
    <AppShell>
      <div className="audit-index-page">
        <nav className="audit-breadcrumb" aria-label="Breadcrumb">
          <Link href="/operator">Home</Link>
          <ChevronRight size={16} />
          <Link href="/audits">Audits</Link>
          <ChevronRight size={16} />
          <span>Processing</span>
        </nav>

        <section className="audit-index-hero">
          <div>
            <span className="eyebrow">Upload processing</span>
            <h1>{status?.fileName ?? "Audit status"}</h1>
            <p>{status ? statusMessage(status.job?.status ?? status.projectStatus) : "TraceReady could not find a queued audit record for this upload."}</p>
          </div>
          <Link className="button large secondary" href="/audits">
            <FileSpreadsheet size={18} />
            All audits
          </Link>
        </section>

        {loadError ? (
          <section className="audit-parse-alert">
            <AlertTriangle size={19} />
            <div>
              <strong>Status unavailable</strong>
              <span>{loadError}</span>
            </div>
          </section>
        ) : null}

        {query?.worker ? (
          <section className="audit-parse-alert">
            <ServerCog size={19} />
            <div>
              <strong>Python worker</strong>
              <span>{query.worker}</span>
            </div>
          </section>
        ) : null}

        {status ? (
          <>
            <section className="audit-index-grid" aria-label="Processing summary">
              <StatusMetric label="Project" status={status.projectStatus} />
              <StatusMetric label="Run" status={status.run?.status ?? "pending"} />
              <StatusMetric label="Python job" status={status.job?.status ?? "pending"} />
            </section>

            <section className="audit-list-card">
              <div className="audit-list-header">
                <div>
                  <h2>Queued workflow</h2>
                  <p>The workbook is stored in private object storage and waiting for the Python parser job.</p>
                </div>
              </div>
              <div className="after-upload-list">
                <ProcessingStep icon={<CheckCircle2 />} title="Workbook stored" detail={status.file?.storageKey ?? status.rawWorkbookKey ?? "Private upload object recorded"} tone="green" />
                <ProcessingStep icon={<Clock3 />} title="Audit records created" detail={`Project ${status.auditProjectId}${status.run ? `, run ${status.run.id}` : ""}`} tone="blue" />
                <ProcessingStep
                  icon={status.job?.status === "failed" ? <AlertTriangle /> : <ServerCog />}
                  title="Python validation job"
                  detail={status.job ? `${status.job.jobType} is ${status.job.status}` : "Job record is pending"}
                  tone={status.job?.status === "failed" ? "amber" : "blue"}
                />
              </div>
              {status.job?.failureCategory || status.job?.error ? (
                <section className="audit-parse-alert">
                  <AlertTriangle size={19} />
                  <div>
                    <strong>{status.job.failureCategory ?? "Job failed"}</strong>
                    <span>{status.job.error ? JSON.stringify(status.job.error) : "No structured error payload was recorded."}</span>
                  </div>
                </section>
              ) : null}
              {status.job?.retryable ? (
                <form action={retryAuditJobAction} className="phase14-inline-form">
                  <input name="auditId" type="hidden" value={status.auditProjectId} />
                  <input name="jobId" type="hidden" value={status.job.id} />
                  <input name="reason" required placeholder="Retry reason" />
                  <button type="submit">Retry job</button>
                </form>
              ) : null}
              {status.job && ["queued", "retryable", "running"].includes(status.job.status) ? (
                <form action={processAuditJobSliceAction} className="phase14-inline-form">
                  <input name="auditId" type="hidden" value={status.auditProjectId} />
                  <button type="submit">Run Python job</button>
                </form>
              ) : null}
              {status.events.length ? (
                <div className="phase14-subpanel">
                  <h3>Job event stream</h3>
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Event</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {status.events.map((event) => (
                        <tr key={event.id}>
                          <td>{formatDateTime(event.createdAt)}</td>
                          <td>{event.eventType}</td>
                          <td>{event.message ?? JSON.stringify(event.payload ?? {})}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              <div className="audit-list-header">
                <p>Created {formatDateTime(status.createdAt)}. Last updated {formatDateTime(status.updatedAt)}.</p>
                <Link className="button compact secondary" href={`/audits/${status.auditProjectId}`}>
                  Open workspace
                  <ChevronRight size={16} />
                </Link>
              </div>
            </section>
          </>
        ) : (
          <section className="audit-list-card">
            <div className="audit-list-header">
              <div>
                <h2>Audit not found</h2>
                <p>This can happen if the upload was not queued or your account is not linked to the audit customer.</p>
              </div>
              <Link className="button compact" href="/upload">
                Upload records
              </Link>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}

function StatusMetric({ label, status }: { label: string; status: string }) {
  const tone = status === "failed" ? "amber" : status === "succeeded" || status === "completed" ? "green" : "blue";
  const icon = status === "failed" ? <AlertTriangle /> : status === "queued" || status === "running" || status === "pending" ? <Loader2 /> : <CheckCircle2 />;
  return (
    <div className={`audit-index-metric ${tone}`}>
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{statusLabel(status)}</strong>
      </div>
    </div>
  );
}

function ProcessingStep({ icon, title, detail, tone }: { icon: React.ReactNode; title: string; detail: string; tone: "blue" | "green" | "amber" }) {
  return (
    <div className="after-upload-item">
      <span className={`after-upload-icon ${tone === "green" ? "green" : tone === "amber" ? "amber" : ""}`}>{icon}</span>
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
      <ChevronRight size={17} />
    </div>
  );
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

function statusMessage(status: string) {
  if (status === "failed") return "The Python job failed and is ready for retry or investigation.";
  if (status === "running") return "The Python backend is parsing, normalizing, and validating this workbook.";
  if (status === "succeeded" || status === "completed") return "The audit processing job completed.";
  return "The workbook has been queued for Python parsing and deterministic approved-rule validation.";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}
