import { AppShell } from "@/components/AppShell";
import { listApprovedRulePackages, listKdeRequirements, listRegulatorySources, listRuleCards } from "@/lib/regulatory/regulatory-admin-db";

export default async function RegulatoryVersionsPage() {
  const [ruleCards, kdeRequirements, sources, packages] = await Promise.all([
    listRuleCards(),
    listKdeRequirements(),
    listRegulatorySources(),
    listApprovedRulePackages()
  ]);
  const rows = [
    ...sources.map((source) => ({
      id: source.id,
      type: "source",
      version: source.text_hash,
      status: source.source_status,
      reviewer: source.is_finalized ? "official source" : "monitor"
    })),
    ...ruleCards.map((rule) => ({
      id: rule.rule_code,
      type: "rule card",
      version: String(rule.version),
      status: rule.status,
      reviewer: rule.reviewed_by ?? "pending"
    })),
    ...kdeRequirements.map((requirement) => ({
      id: requirement.id,
      type: "KDE requirement",
      version: String(requirement.version),
      status: requirement.status,
      reviewer: requirement.reviewed_by ?? "pending"
    })),
    ...packages.map((pkg) => ({
      id: pkg.package_id,
      type: "approved package",
      version: String(pkg.version),
      status: pkg.status,
      reviewer: pkg.approved_by
    }))
  ];

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Regulatory Versions</h1>
          <p className="muted">Published source, rule-card, and KDE versions used by customer audits.</p>
        </div>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Version / Hash</th>
              <th>Status</th>
              <th>Reviewer</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.type}-${row.id}`}>
                <td>{row.id}</td>
                <td>{row.type}</td>
                <td>{row.version}</td>
                <td>{row.status}</td>
                <td>{row.reviewer}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
