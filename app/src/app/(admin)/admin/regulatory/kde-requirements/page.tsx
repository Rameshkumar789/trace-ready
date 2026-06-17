import { AppShell } from "@/components/AppShell";
import { listKdeRequirements } from "@/lib/regulatory/regulatory-admin-db";

export default async function KdeRequirementsPage() {
  const kdeRequirements = await listKdeRequirements();
  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>KDE Requirement Dictionary</h1>
          <p className="muted">Approved CTE/KDE cards that the deterministic audit engine can execute.</p>
        </div>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>KDE</th>
              <th>CTE</th>
              <th>Status</th>
              <th>Rule</th>
              <th>Citation</th>
              <th>Validation</th>
            </tr>
          </thead>
          <tbody>
            {kdeRequirements.map((requirement) => {
              return (
                <tr key={requirement.id}>
                  <td>{requirement.kde_name}</td>
                  <td>{requirement.cte_type}</td>
                  <td>{requirement.status}</td>
                  <td>{requirement.rule_card_id}</td>
                  <td>{requirement.source_chunk_id}</td>
                  <td><span className={`badge ${requirement.status === "approved" ? "ok" : "warn"}`}>{requirement.status === "approved" ? "approved" : "review required"}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
