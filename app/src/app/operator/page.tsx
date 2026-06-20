import {
  CircleCheck,
  FileText,
  FileWarning,
  Link2Off,
  ListChecks,
  ShieldCheck,
  Table2,
  TriangleAlert,
  Upload,
  Workflow,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { loadOperatorAuditDashboard, type OperatorAuditDashboard } from "@/lib/audit/operator-audit-db";
import { Button, Card, CoverageRing, PageHeader, StatCard } from "@/components/ui";

const outputs = [
  { title: "Missing KDE report", detail: "See which required data is missing.", Icon: FileWarning },
  { title: "TLC gaps", detail: "Find missing or broken lot codes.", Icon: Link2Off },
  { title: "Exception list", detail: "All issues in one review queue.", Icon: ListChecks },
  { title: "Sortable export", detail: "FDA-style package with citations.", Icon: Table2 },
] as const;

export default async function OperatorDashboardPage() {
  const session = await getTraceReadySession();
  const workspaceName = session?.fullName ?? session?.email ?? "your team";
  const d = session ? await loadDashboard(session) : emptyDashboard();
  const readiness = d.totalAudits > 0 ? (d.readyExports / d.totalAudits) * 100 : 0;

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <PageHeader
          eyebrow="Operator"
          title={`Welcome back, ${workspaceName}.`}
          subtitle="Get traceability-ready by uploading your records and running an FSMA 204 readiness audit."
          actions={
            <>
              <Button href="/upload" icon={<Upload size={18} />} size="lg">
                Upload records
              </Button>
              <Button href="/audits/demo/report" variant="secondary" size="lg" icon={<FileText size={18} />}>
                View sample output
              </Button>
            </>
          }
        />

        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-label="Readiness snapshot">
          <StatCard label="Audits" value={d.totalAudits} hint="Uploaded workbooks" icon={<ShieldCheck size={18} />} tone="accent" />
          <StatCard label="Processing" value={d.queuedJobs + d.runningJobs} hint="Queued or running" icon={<Workflow size={18} />} />
          <StatCard
            label="Open findings"
            value={d.openFindings}
            hint="Gaps needing review"
            icon={<TriangleAlert size={18} />}
            tone={d.openFindings ? "review" : "ok"}
          />
          <StatCard
            label="Ready exports"
            value={d.readyExports}
            hint="Completed packages"
            icon={<CircleCheck size={18} />}
            tone={d.readyExports ? "ok" : "neutral"}
          />
        </section>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
          <Card padding="lg" className="flex flex-col">
            <h3 className="text-lg font-bold text-ink">Start a readiness audit</h3>
            <p className="mt-1 text-sm text-muted">
              Upload a workbook or mapped export from your system. We will check scope, events, KDEs,
              TLCs, and evidence.
            </p>
            <a
              href="/upload"
              className="mt-4 flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-line bg-surface px-6 py-10 text-center transition-colors hover:bg-surface-strong"
            >
              <span className="grid h-12 w-12 place-items-center rounded-card bg-accent-soft text-accent">
                <Upload size={22} />
              </span>
              <strong className="text-ink">Drag and drop file here</strong>
              <span className="text-sm text-muted">or click to browse</span>
            </a>
            <small className="mt-3 text-xs text-muted">Supported: .xlsx, .xlsm &nbsp;|&nbsp; Max size: 10 MB</small>
          </Card>

          <div className="flex flex-col gap-6">
            <Card padding="lg" className="flex flex-col items-center text-center">
              <h3 className="mb-3 self-start text-sm font-semibold text-ink">Readiness</h3>
              <CoverageRing value={readiness} label={`${d.readyExports} of ${d.totalAudits} audits export-ready`} />
            </Card>

            <Card padding="md">
              <h3 className="mb-3 text-sm font-semibold text-ink">What you will get</h3>
              <ul className="flex flex-col gap-3">
                {outputs.map(({ title, detail, Icon }) => (
                  <li key={title} className="flex items-start gap-3">
                    <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-card bg-surface-strong text-accent">
                      <Icon size={16} />
                    </span>
                    <div>
                      <strong className="text-sm text-ink">{title}</strong>
                      <p className="text-xs text-muted">{detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
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
    readyExports: 0,
  };
}
