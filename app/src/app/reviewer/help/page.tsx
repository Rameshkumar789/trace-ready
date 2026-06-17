import Link from "next/link";
import { AppShell } from "@/components/AppShell";

const helpItems = [
  ["Rule review", "Approve only source-backed rule cards with complete citations and scenario coverage."],
  ["KDE requirements", "Review field requirements before they become executable audit checks."],
  ["Publication gate", "Use coverage and scenario tests to prevent silent rule drift."]
] as const;

export default function ReviewerHelpPage() {
  return (
    <AppShell>
      <section className="utility-page">
        <div className="utility-header">
          <span className="eyebrow">Help</span>
          <h1>Reviewer console support.</h1>
          <p>Guidance for source review, rule-card approval, KDE requirements, and scenario coverage.</p>
        </div>
        <div className="utility-grid">
          {helpItems.map(([title, detail]) => (
            <article className="utility-card" key={title}>
              <h2>{title}</h2>
              <p>{detail}</p>
            </article>
          ))}
        </div>
        <Link className="button" href="/admin/regulatory/review">Open review queue</Link>
      </section>
    </AppShell>
  );
}
