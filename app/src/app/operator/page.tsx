import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { CircleCheck, FileText, FileWarning, Link2Off, ListChecks, ShieldCheck, Table2, TriangleAlert, Upload, Workflow } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { loadOperatorAuditDashboard, type OperatorAuditDashboard } from "@/lib/audit/operator-audit-db";

const outputs = [
  ["Missing KDE report", "See which required data is missing.", "kdeReport"],
  ["TLC gaps", "Find missing or broken lot codes.", "tlcGap"],
  ["Exception list", "All issues in one review queue.", "exceptionList"],
  ["Sortable export", "FDA-style package with citations.", "sortableExport"]
] as const;

const miniIcons: Record<string, LucideIcon> = {
  upload: Upload,
  document: FileText,
  scope: ShieldCheck,
  events: Workflow,
  warning: TriangleAlert,
  ready: CircleCheck,
  kdeReport: FileWarning,
  tlcGap: Link2Off,
  exceptionList: ListChecks,
  sortableExport: Table2
};

export default async function OperatorDashboardPage() {
  const session = await getTraceReadySession();
  const workspaceName = session?.fullName ?? session?.email ?? "your team";
  const dashboard = session ? await loadDashboard(session) : emptyDashboard();
  const snapshotRows = buildSnapshotRows(dashboard);

  return (
    <AppShell>
      <section className="home-dashboard">
        <div className="home-primary">
          <section className="welcome-panel">
            <h2>Welcome back, {workspaceName}.</h2>
            <p>Get traceability-ready by uploading your records and running an FSMA 204 readiness audit.</p>
            <div className="welcome-actions">
              <Link className="button large" href="/upload">
                <MiniIcon name="upload" />
                Upload records
              </Link>
              <Link className="button secondary large" href="/audits/demo/report">
                <MiniIcon name="document" />
                View sample output
              </Link>
            </div>
          </section>

          <Link className="audit-start-card" href="/upload">
            <h3>Start a readiness audit</h3>
            <p>
              Upload a workbook or mapped export from your system. We will check scope, events, KDEs, TLCs, and evidence.
            </p>
            <div className="upload-drop-card">
              <MiniIcon name="upload" />
              <strong>Drag and drop file here</strong>
              <span>or click to browse</span>
            </div>
            <small>Supported: .xlsx, .xlsm &nbsp; | &nbsp; Max size: 10 MB</small>
          </Link>
        </div>

        <aside className="home-side">
          <section className="side-card readiness-card">
            <h3>
              Readiness snapshot
              <span aria-hidden="true">i</span>
            </h3>
            <div className="snapshot-list">
              {snapshotRows.map(([title, detail, status, tone, icon]) => (
                <div className="snapshot-row" key={title}>
                  <MiniIcon name={icon} tone={tone} />
                  <div>
                    <strong>{title}</strong>
                    <span>{detail}</span>
                  </div>
                  <em className={tone === "amber" ? "warn" : ""}>{status}</em>
                </div>
              ))}
            </div>
          </section>

          <section className="side-card output-card">
            <h3>What you will get</h3>
            <div className="output-list">
              {outputs.map(([title, detail, icon]) => (
                <div className="output-row" key={title}>
                  <MiniIcon name={icon} />
                  <div>
                    <strong>{title}</strong>
                    <span>{detail}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </aside>

      </section>
    </AppShell>
  );
}

function MiniIcon({ name, tone = "blue" }: { name: string; tone?: string }) {
  const Icon = miniIcons[name] ?? FileText;

  return (
    <span className={`mini-symbol ${tone}`} aria-hidden="true">
      <Icon aria-hidden="true" strokeWidth={2.1} />
    </span>
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

function buildSnapshotRows(dashboard: OperatorAuditDashboard) {
  return [
    ["Audits", "Uploaded workbooks", String(dashboard.totalAudits), "blue", "scope"],
    ["Processing", "Queued or running jobs", String(dashboard.queuedJobs + dashboard.runningJobs), "blue", "events"],
    ["Open findings", "Gaps needing review", String(dashboard.openFindings), dashboard.openFindings ? "amber" : "green", dashboard.openFindings ? "warning" : "ready"],
    ["Ready exports", "Completed packages", String(dashboard.readyExports), dashboard.readyExports ? "green" : "blue", "ready"]
  ] as const;
}
