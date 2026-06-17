import Link from "next/link";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadReviewerWorkbenchData } from "@/lib/regulatory/regulatory-admin-db";

export default async function ReviewerFindingsPage() {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, "/reviewer/findings")) {
    redirect("/login/reviewer?auth=required&next=/reviewer/findings");
  }
  const data = await loadReviewerWorkbenchData(250);
  const findings = data.queueItems.filter((item) => item.objectType === "customer_finding");

  return (
    <AppShell>
      <div className="reviewer-workbench-page">
        <section className="reviewer-workbench-header compact">
          <div>
            <span className="eyebrow">Finding Reviews</span>
            <h1>Customer findings that need expert review.</h1>
            <p>These rows come from live audit findings and open the existing audit review decision screen.</p>
          </div>
          <Link className="button secondary" href="/reviewer">Back to Workbench</Link>
        </section>

        <section className="reviewer-queue-panel">
          <div className="reviewer-queue-heading">
            <div>
              <h2>Open customer finding reviews</h2>
              <p>Review gaps, evidence issues, and reviewer-routed customer findings.</p>
            </div>
            <span className="badge warn">{findings.length} open</span>
          </div>

          {findings.length ? (
            <div className="reviewer-table-wrap">
              <table className="reviewer-queue-table">
                <thead>
                  <tr>
                    <th>Priority</th>
                    <th>Finding</th>
                    <th>Citation</th>
                    <th>Status</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((finding) => (
                    <tr key={finding.id}>
                      <td><span className={`reviewer-priority ${finding.priority}`}>{finding.priority}</span></td>
                      <td>
                        <Link className="reviewer-object-link" href={finding.targetHref}>
                          <strong>{finding.label}</strong>
                          <span>{finding.subtitle}</span>
                        </Link>
                      </td>
                      <td>{finding.citation}</td>
                      <td>
                        <span className="review-status">{finding.status}</span>
                        <small>{finding.owner}</small>
                      </td>
                      <td>{formatDate(finding.updatedAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="reviewer-empty-state">
              <h2>No customer findings are waiting for reviewer action.</h2>
              <p>The page is connected to `audit_findings`; new reviewer-routed findings will appear here.</p>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(date);
}
