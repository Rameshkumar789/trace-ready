import { AppShell } from "@/components/AppShell";
import { listScenarioCases, listScenarioRegressionRuns } from "@/lib/regulatory/regulatory-admin-db";

export default async function ScenariosPage() {
  const [scenarios, runs] = await Promise.all([listScenarioCases(), listScenarioRegressionRuns()]);
  const latestRun = runs[0];
  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Scenario Runner</h1>
          <p className="muted">Regression fixtures prove rule cards before findings become customer-facing.</p>
        </div>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Expected</th>
              <th>Actual</th>
              <th>Result</th>
              <th>Citations</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
                <tr key={scenario.id}>
                  <td>{scenario.name}</td>
                  <td>{scenario.expected_status}</td>
                  <td>{latestRun?.status ?? "not run"}</td>
                  <td>
                    <span className={`badge ${scenario.status === "approved" ? "ok" : "warn"}`}>
                      {scenario.status}
                    </span>
                  </td>
                  <td>{scenario.scenario_group}</td>
                </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
