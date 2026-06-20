import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileSpreadsheet,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { listOperatorAuditSummaries, type OperatorAuditSummary } from "@/lib/audit/operator-audit-db";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  PageHeader,
  StatCard,
  StatusPill,
  type Column,
} from "@/components/ui";

export default async function AuditsPage() {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, "/audits")) {
    redirect("/login/operator?auth=required&next=/audits");
  }
  const { auditRows, loadError } = await loadAuditRows(session);

  const openFindings = auditRows.reduce((sum, audit) => sum + audit.findingsCount, 0);
  const readyExports = auditRows.filter((audit) => audit.readinessPassed).length;

  const columns: Column<OperatorAuditSummary>[] = [
    {
      key: "status",
      header: "Status",
      cell: (a) =>
        a.readinessPassed ? (
          <StatusPill tone="ok" icon={<CheckCircle2 size={14} />}>
            Ready
          </StatusPill>
        ) : (
          <StatusPill tone="review" icon={<AlertTriangle size={14} />}>
            Action needed
          </StatusPill>
        ),
    },
    {
      key: "file",
      header: "File",
      cell: (a) => (
        <div>
          <div className="font-semibold text-ink">{a.fileName}</div>
          <div className="text-xs text-muted">{a.auditId}</div>
        </div>
      ),
    },
    { key: "created", header: "Created", cell: (a) => <span className="text-muted">{formatDate(a.createdAt)}</span> },
    {
      key: "stage",
      header: "Stage",
      cell: (a) => <span className="capitalize text-muted">{a.jobStatus ?? a.status}</span>,
    },
    {
      key: "counts",
      header: "Findings",
      align: "right",
      cell: (a) => (
        <div className="text-right">
          <div className="font-semibold text-ink">{a.findingsCount}</div>
          <div className="text-xs text-muted">{a.blockerCount} blockers</div>
        </div>
      ),
    },
    { key: "chevron", header: "", align: "right", cell: () => <ChevronRight size={18} className="text-muted" /> },
  ];

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <PageHeader
          eyebrow="Audits"
          title="Traceability readiness audits"
          subtitle="Open an audit to resolve findings, review evidence, and export the readiness package."
          actions={
            <Button href="/upload" icon={<Upload size={18} />} size="lg">
              Upload records
            </Button>
          }
        />

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3" aria-label="Audit summary">
          <StatCard label="Total audits" value={auditRows.length} icon={<FileSpreadsheet size={18} />} tone="accent" />
          <StatCard label="Open findings" value={openFindings} icon={<AlertTriangle size={18} />} tone="review" />
          <StatCard label="Ready exports" value={readyExports} icon={<ShieldCheck size={18} />} tone="ok" />
        </section>

        {loadError ? (
          <Card accent="risk" className="flex items-start gap-3">
            <AlertTriangle size={19} className="mt-0.5 shrink-0 text-risk" />
            <div>
              <strong className="text-ink">Audit list unavailable</strong>
              <p className="mt-0.5 text-sm text-muted">{loadError}</p>
            </div>
          </Card>
        ) : null}

        <DataTable
          columns={columns}
          rows={auditRows}
          rowKey={(a) => a.auditId}
          rowHref={(a) => `/audits/${a.auditId}`}
          empty={
            <EmptyState
              icon={<FileSpreadsheet size={28} />}
              title="No uploaded audits yet"
              body="Upload a workbook to create a database-backed audit job."
              action={
                <Button href="/upload" icon={<Upload size={16} />} variant="secondary">
                  Upload records
                </Button>
              }
            />
          }
        />
      </div>
    </AppShell>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(value),
  );
}

async function loadAuditRows(session: NonNullable<Awaited<ReturnType<typeof getPilotSession>>>): Promise<{
  auditRows: OperatorAuditSummary[];
  loadError?: string;
}> {
  try {
    return { auditRows: await listOperatorAuditSummaries(session) };
  } catch (error) {
    return {
      auditRows: [],
      loadError:
        error instanceof Error ? error.message : "Unable to read audit projects from Supabase.",
    };
  }
}
