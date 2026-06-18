import Link from "next/link";
import { ArrowUp, Upload, FileWarning, Link2Off, ListChecks, Table2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { loadOperatorAuditDashboard, type OperatorAuditDashboard } from "@/lib/audit/operator-audit-db";

const outputs = [
  ["Missing KDE report", "See which required data is missing.", FileWarning],
  ["TLC gaps", "Find missing or broken lot codes.", Link2Off],
  ["Exception list", "All issues in one review queue.", ListChecks],
  ["Sortable export", "FDA-style package with citations.", Table2]
] as const;

export default async function OperatorDashboardPage() {
  const session = await getTraceReadySession();
  const workspaceName = session?.fullName ?? session?.email ?? "your team";
  const dashboard = session ? await loadDashboard(session) : emptyDashboard();
  const processing = dashboard.queuedJobs + dashboard.runningJobs;

  return (
    <AppShell>
      <div className="tr-page">
        <header className="tr-head">
          <div>
            <h1>Welcome back, {workspaceName}.</h1>
            <p className="tr-sub">Upload your records to run an FSMA 204 readiness audit — or ask anything about the rule.</p>
          </div>
          <span className="tr-trust">Grounded in 21 CFR Subpart S</span>
        </header>

        <Link className="tr-ask" href="/operator/ask">
          <span className="tr-ask-text">Ask about FSMA 204, or your own records…</span>
          <span className="tr-ask-send" aria-hidden="true"><ArrowUp size={16} /></span>
        </Link>

        <div className="tr-metrics">
          <Link className="tr-metric" href="/audits">
            <span className="tr-metric-label">Audits</span>
            <strong>{dashboard.totalAudits}</strong>
          </Link>
          <div className="tr-metric">
            <span className="tr-metric-label">Processing</span>
            <strong>{processing}</strong>
          </div>
          <div className="tr-metric">
            <span className="tr-metric-label">Open findings</span>
            <strong className={dashboard.openFindings ? "tr-amber" : ""}>{dashboard.openFindings}</strong>
          </div>
          <div className="tr-metric">
            <span className="tr-metric-label">Ready exports</span>
            <strong>{dashboard.readyExports}</strong>
          </div>
        </div>

        <Link className="tr-upload" href="/upload">
          <span className="tr-upload-icon" aria-hidden="true"><Upload size={22} /></span>
          <strong>Start a readiness audit</strong>
          <span className="tr-upload-hint">Drag and drop a workbook, or click to browse</span>
          <small>Supported: .xlsx, .xlsm · Max size 10 MB</small>
        </Link>

        <section className="tr-outputs">
          <h2 className="tr-section-label">What you’ll get</h2>
          <div className="tr-output-grid">
            {outputs.map(([title, detail, Icon]) => (
              <div className="tr-output" key={title}>
                <span className="tr-output-icon" aria-hidden="true"><Icon size={18} /></span>
                <div>
                  <strong>{title}</strong>
                  <span>{detail}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

async function loadDashboard(session: NonNullable<Awaited<ReturnType<typeof getTraceReadySession>>>) {
  try {
    return await loadOperatorAuditDashboard(session);
  } catch {
    return emptyDashboard();
  }
}

function emptyDashboard(): OperatorAuditDashboard {
  return {
    totalAudits: 0,
    queuedJobs: 0,
    runningJobs: 0,
    failedJobs: 0,
    openFindings: 0,
    readyExports: 0
  };
}
