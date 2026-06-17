import Link from "next/link";
import { AppShell } from "@/components/AppShell";

const helpItems = [
  ["Upload format", "Use Excel, CSV, or mapped exports from EDI, WMS, or ERP systems."],
  ["Audit output", "TraceReady returns missing KDEs, TLC gaps, exception lists, and sortable exports."],
  ["Pilot support", "For pilot issues, send the workbook name and audit ID to the TraceReady team."]
] as const;

export default function OperatorHelpPage() {
  return (
    <AppShell>
      <section className="utility-page">
        <div className="utility-header">
          <span className="eyebrow">Help</span>
          <h1>Get support for readiness audits.</h1>
          <p>Short answers for the operator workflow. This will become a searchable help center as pilots grow.</p>
        </div>
        <div className="utility-grid">
          {helpItems.map(([title, detail]) => (
            <article className="utility-card" key={title}>
              <h2>{title}</h2>
              <p>{detail}</p>
            </article>
          ))}
        </div>
        <Link className="button" href="/upload">Start an audit</Link>
      </section>
    </AppShell>
  );
}
