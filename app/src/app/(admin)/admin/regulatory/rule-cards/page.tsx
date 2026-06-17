import { AppShell } from "@/components/AppShell";
import { listRuleCards } from "@/lib/regulatory/regulatory-admin-db";

export default async function RuleCardsPage() {
  const ruleCards = await listRuleCards();
  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Rule Card Workbench</h1>
          <p className="muted">AI drafts remain drafts; only reviewed rule cards can power customer-facing findings.</p>
        </div>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Area</th>
              <th>Status</th>
              <th>Version</th>
              <th>Validation</th>
            </tr>
          </thead>
          <tbody>
            {ruleCards.map((ruleCard) => {
              return (
                <tr key={ruleCard.id}>
                  <td>{ruleCard.rule_code}</td>
                  <td>{ruleCard.rule_area}</td>
                  <td>{ruleCard.status}</td>
                  <td>{ruleCard.version}</td>
                  <td>
                    <span className={`badge ${ruleCard.status === "approved" && ruleCard.is_finalized_source ? "ok" : "warn"}`}>
                      {ruleCard.status === "approved" && ruleCard.is_finalized_source ? "approved final" : "review required"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
