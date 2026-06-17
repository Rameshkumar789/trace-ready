import { AppShell } from "@/components/AppShell";
import { loadRegulatoryCoverageSummary } from "@/lib/regulatory/regulatory-admin-db";
import { publishApprovedRulePackageAction } from "../review/actions";

export default async function CoveragePage() {
  const summary = await loadRegulatoryCoverageSummary();
  const coverageRows = [
    ["Draft records", summary.draftRecords, `${summary.rejectedRecords} rejected by validation gate`],
    ["Ready for review", summary.readyForReview, "Schema-valid and citation-valid drafts awaiting FSMA expert action"],
    ["Reviewer status model", Object.keys(summary.statusCounts).length, Object.entries(summary.statusCounts).map(([status, count]) => `${status}: ${count}`).join(", ")],
    ["Scenario regression", summary.latestScenarioRun?.benchmark_count ?? 0, summary.latestScenarioRun ? `${summary.latestScenarioRun.pass_count} pass / ${summary.latestScenarioRun.fail_count} fail` : "No persisted run"],
    ["Approved packages", summary.approvedPackages, "Published approved-rule package records"]
  ] as const;
  const blocked = summary.approvedPackages === 0;

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Regulatory Coverage Gate</h1>
          <p className="muted">Shows whether extracted regulatory intelligence can move from draft validation into reviewer approval.</p>
        </div>
        <span className={`badge ${blocked ? "warn" : "ok"}`}>
          {blocked ? "approval required" : "approved package ready"}
        </span>
      </div>
      <section className="panel">
        <h2>Package publication</h2>
        <form action={publishApprovedRulePackageAction} className="phase14-inline-form">
          <input name="reason" required placeholder="Publication reason" />
          <button type="submit" disabled={summary.approvedRecords === 0}>Publish approved package</button>
        </form>
      </section>
      <section className="grid two">
        <div className="panel">
          <h2>Phase 6 Controls</h2>
          <table>
            <tbody>
              {coverageRows.map(([area, value, reason]) => (
                <tr key={area}>
                  <td>{area}</td>
                  <td>{value}</td>
                  <td>{reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h2>Gate Blockers</h2>
          <ul>
            <li>Product audit engine must read approved records only.</li>
            <li>{summary.readyForReview} records still require FSMA expert approval.</li>
            <li>{summary.rejectedRecords} rejected records need correction or replacement before approval.</li>
          </ul>
        </div>
      </section>
    </AppShell>
  );
}
