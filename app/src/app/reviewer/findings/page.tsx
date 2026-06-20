import { redirect } from "next/navigation";
import { ClipboardList } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadReviewerWorkbenchData } from "@/lib/regulatory/regulatory-admin-db";
import {
  Button,
  DataTable,
  EmptyState,
  PageHeader,
  StatusPill,
  type Column,
  type Tone,
} from "@/components/ui";

type QueueItem = Awaited<ReturnType<typeof loadReviewerWorkbenchData>>["queueItems"][number];

const priorityTone = (p: string): Tone =>
  p === "high" ? "risk" : p === "medium" ? "review" : "neutral";

export default async function ReviewerFindingsPage() {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, "/reviewer/findings")) {
    redirect("/login/reviewer?auth=required&next=/reviewer/findings");
  }
  const data = await loadReviewerWorkbenchData(250);
  const findings = data.queueItems.filter((item) => item.objectType === "customer_finding");

  const columns: Column<QueueItem>[] = [
    {
      key: "priority",
      header: "Priority",
      cell: (f) => (
        <StatusPill tone={priorityTone(f.priority)} className="capitalize">
          {f.priority}
        </StatusPill>
      ),
    },
    {
      key: "finding",
      header: "Finding",
      cell: (f) => (
        <div>
          <div className="font-semibold text-ink">{f.label}</div>
          <div className="text-xs text-muted">{f.subtitle}</div>
        </div>
      ),
    },
    { key: "citation", header: "Citation", cell: (f) => <span className="text-muted">{f.citation}</span> },
    {
      key: "status",
      header: "Status",
      cell: (f) => (
        <div>
          <div className="capitalize text-ink">{f.status}</div>
          <div className="text-xs text-muted">{f.owner}</div>
        </div>
      ),
    },
    { key: "updated", header: "Updated", cell: (f) => <span className="text-muted">{formatDate(f.updatedAt)}</span> },
  ];

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <PageHeader
          eyebrow="Finding Reviews"
          title="Customer findings that need expert review"
          subtitle="These rows come from live audit findings and open the audit review decision screen."
          actions={
            <Button href="/reviewer" variant="secondary">
              Back to Workbench
            </Button>
          }
        />

        <DataTable
          columns={columns}
          rows={findings}
          rowKey={(f) => f.id}
          rowHref={(f) => f.targetHref}
          empty={
            <EmptyState
              icon={<ClipboardList size={28} />}
              title="No customer findings are waiting for reviewer action"
              body="This view is connected to audit findings; new reviewer-routed findings will appear here."
            />
          }
        />
      </div>
    </AppShell>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(
    date,
  );
}
