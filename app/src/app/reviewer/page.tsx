import { redirect } from "next/navigation";
import { CheckCircle2, FileStack, FileX2, FlagTriangleRight, Inbox } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadReviewerWorkbenchData } from "@/lib/regulatory/regulatory-admin-db";
import {
  DataTable,
  EmptyState,
  PageHeader,
  SectionHeader,
  StatCard,
  StatusPill,
  type Column,
  type Tone,
} from "@/components/ui";

type QueueItem = Awaited<ReturnType<typeof loadReviewerWorkbenchData>>["queueItems"][number];

const priorityRank: Record<string, number> = { high: 0, medium: 1, low: 2 };
const priorityTone = (p: string): Tone =>
  p === "high" ? "risk" : p === "medium" ? "review" : "neutral";

export default async function ReviewerDashboardPage() {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, "/reviewer")) {
    redirect("/login/reviewer?auth=required&next=/reviewer");
  }
  const data = await loadReviewerWorkbenchData(80);

  const queue = [...data.queueItems]
    .sort((a, b) => (priorityRank[a.priority] ?? 9) - (priorityRank[b.priority] ?? 9))
    .slice(0, 8);

  const columns: Column<QueueItem>[] = [
    {
      key: "priority",
      header: "Priority",
      cell: (q) => (
        <StatusPill tone={priorityTone(q.priority)} className="capitalize">
          {q.priority}
        </StatusPill>
      ),
    },
    {
      key: "item",
      header: "Item",
      cell: (q) => (
        <div>
          <div className="font-semibold text-ink">{q.label}</div>
          <div className="text-xs text-muted">{q.subtitle}</div>
        </div>
      ),
    },
    { key: "type", header: "Type", cell: (q) => <span className="capitalize text-muted">{q.objectType.replace(/_/g, " ")}</span> },
    { key: "citation", header: "Citation", cell: (q) => <span className="text-muted">{q.citation}</span> },
  ];

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <PageHeader
          eyebrow="Reviewer Workbench"
          title="Expert review for rules, citations, and customer findings"
          subtitle="Approve source-backed regulatory intelligence before it can become executable, then review customer-facing findings that need expert judgment."
        />

        <section className="grid grid-cols-2 gap-4 lg:grid-cols-5" aria-label="Reviewer summary">
          <StatCard label="Total Records" value={data.summary.regulatoryDrafts} icon={<FileStack size={18} />} />
          <StatCard
            label="Open Drafts"
            value={data.draftQueueTotal}
            hint="awaiting reviewer action"
            tone="review"
            icon={<Inbox size={18} />}
            href="/admin/regulatory/review"
          />
          <StatCard label="High priority" value={data.highPriorityTotal} tone="risk" icon={<FlagTriangleRight size={18} />} />
          <StatCard label="Approved" value={data.summary.approvedRecords} tone="ok" icon={<CheckCircle2 size={18} />} />
          <StatCard label="Rejected" value={data.summary.rejectedRecords} tone="risk" icon={<FileX2 size={18} />} />
        </section>

        <section className="flex flex-col gap-3">
          <SectionHeader
            title="Top of the review queue"
            hint="Highest-priority drafts and customer findings"
            actions={
              <a href="/reviewer/findings" className="text-sm font-semibold text-accent">
                View all findings →
              </a>
            }
          />
          <DataTable
            columns={columns}
            rows={queue}
            rowKey={(q) => q.id}
            rowHref={(q) => q.targetHref}
            empty={
              <EmptyState
                icon={<Inbox size={28} />}
                title="The review queue is clear"
                body="New regulatory drafts and reviewer-routed findings will appear here."
              />
            }
          />
        </section>
      </div>
    </AppShell>
  );
}
