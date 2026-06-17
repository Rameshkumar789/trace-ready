import Link from "next/link";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadReviewerWorkbenchData } from "@/lib/regulatory/regulatory-admin-db";

export default async function ReviewerDashboardPage() {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, "/reviewer")) {
    redirect("/login/reviewer?auth=required&next=/reviewer");
  }
  const data = await loadReviewerWorkbenchData(80);

  return (
    <AppShell>
      <div className="reviewer-workbench-page">
        <section className="reviewer-workbench-header">
          <div>
            <span className="eyebrow">Reviewer Workbench</span>
            <h1>Expert review for rules, citations, and customer findings.</h1>
            <p>
              Consultants and legal reviewers approve source-backed regulatory intelligence before it can become executable, then review customer-facing findings that need expert judgment.
            </p>
          </div>
        </section>

        <section className="reviewer-triage" aria-label="Reviewer workbench summary">
          <ReviewerSummaryCard label="Total Records" value={data.summary.regulatoryDrafts} />
          <ReviewerSummaryCard href="/admin/regulatory/review" label="Open Drafts" value={data.draftQueueTotal} detail="awaiting reviewer action" />
          <ReviewerSummaryCard label="Approved" value={data.summary.approvedRecords} detail="approved regulatory records" />
          <ReviewerSummaryCard label="Rejected" value={data.summary.rejectedRecords} detail="returned for correction" />
        </section>
      </div>
    </AppShell>
  );
}

function ReviewerSummaryCard({ href, label, value, detail }: { href?: string; label: string; value: number | string; detail?: string }) {
  const content = (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </>
  );
  return href ? (
    <Link className="reviewer-triage-card summary-link" href={href}>
      {content}
    </Link>
  ) : (
    <div className="reviewer-triage-card">
      {content}
    </div>
  );
}
