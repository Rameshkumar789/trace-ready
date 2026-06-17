import Link from "next/link";
import type React from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, FileSpreadsheet, ShieldCheck, Upload } from "lucide-react";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { listOperatorAuditSummaries, type OperatorAuditSummary } from "@/lib/audit/operator-audit-db";

export default async function AuditsPage() {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, "/audits")) {
    redirect("/login/operator?auth=required&next=/audits");
  }
  const { auditRows, loadError } = await loadAuditRows(session);

  return (
    <AppShell>
      <div className="audit-index-page">
        <section className="audit-index-hero">
          <div>
            <span className="eyebrow">Audits</span>
            <h1>Traceability readiness audits</h1>
            <p>Open an audit to resolve findings, review evidence, and export the readiness package.</p>
          </div>
          <Link className="button large" href="/upload">
            <Upload size={18} />
            Upload records
          </Link>
        </section>

        <section className="audit-index-grid" aria-label="Audit summary">
          <AuditIndexMetric icon={<FileSpreadsheet />} label="Total audits" value={String(auditRows.length)} tone="blue" />
          <AuditIndexMetric icon={<AlertTriangle />} label="Open findings" value={String(auditRows.reduce((sum, audit) => sum + audit.findingsCount, 0))} tone="amber" />
          <AuditIndexMetric icon={<ShieldCheck />} label="Ready exports" value={String(auditRows.filter((audit) => audit.readinessPassed).length)} tone="green" />
        </section>

        {loadError ? (
          <section className="audit-parse-alert">
            <AlertTriangle size={19} />
            <div>
              <strong>Audit list unavailable</strong>
              <span>{loadError}</span>
            </div>
          </section>
        ) : null}

        <section className="audit-list-card">
          <div className="audit-list-header">
            <div>
              <h2>All audits</h2>
              <p>Click an audit to open the resolution workspace.</p>
            </div>
          </div>
          <div className="audit-list">
            {auditRows.length ? auditRows.map((audit) => (
              <Link className="audit-list-row" href={`/audits/${audit.auditId}`} key={audit.auditId}>
                <div className={`audit-list-status ${audit.readinessPassed ? "ready" : "review"}`} aria-hidden="true">
                  {audit.readinessPassed ? <CheckCircle2 size={22} /> : <AlertTriangle size={22} />}
                </div>
                <div className="audit-list-main">
                  <strong>{audit.fileName}</strong>
                  <span>{audit.auditId}</span>
                </div>
                <div className="audit-list-meta">
                  <span>{formatDate(audit.createdAt)}</span>
                  <span>{audit.jobStatus ?? audit.status}</span>
                </div>
                <div className="audit-list-counts">
                  <span>{audit.findingsCount} findings</span>
                  <span>{audit.blockerCount} blockers</span>
                </div>
                <ChevronRight size={20} />
              </Link>
            )) : (
              <div className="empty-finding-state">
                <FileSpreadsheet size={32} />
                <strong>No uploaded audits yet</strong>
                <span>Upload a workbook to create a DB-backed audit job.</span>
              </div>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function AuditIndexMetric({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: "blue" | "amber" | "green" }) {
  return (
    <div className={`audit-index-metric ${tone}`}>
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

async function loadAuditRows(session: NonNullable<Awaited<ReturnType<typeof getPilotSession>>>): Promise<{
  auditRows: OperatorAuditSummary[];
  loadError?: string;
}> {
  try {
    return { auditRows: await listOperatorAuditSummaries(session) };
  } catch (error) {
    return { auditRows: [], loadError: error instanceof Error ? error.message : "Unable to read audit projects from Supabase." };
  }
}
