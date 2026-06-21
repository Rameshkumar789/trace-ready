import Link from "next/link";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF } from "@/components/bellwether/brand";

const helpItems = [
  ["Upload format", "Use Excel, CSV, or mapped exports from EDI, WMS, or ERP systems."],
  ["Audit output", "Bellwether returns missing KDEs, TLC gaps, exception lists, and sortable exports."],
  ["Pilot support", "For pilot issues, send the workbook name and audit ID to the Bellwether team."]
] as const;

export default function OperatorHelpPage() {
  return (
    <BellwetherShell topbarLeft="HELP">
      <div style={{ padding: "28px", maxWidth: 900 }}>
        <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Help</span>
        <h1 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>Get support for readiness audits.</h1>
        <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 14.5, lineHeight: 1.6, maxWidth: 560 }}>
          Short answers for the operator workflow. This will become a searchable help center as pilots grow.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 13, marginTop: 22 }}>
          {helpItems.map(([title, detail]) => (
            <article key={title} style={{ background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12, padding: 18 }}>
              <h2 style={{ margin: 0, fontFamily: SERIF, fontSize: 17, fontWeight: 600 }}>{title}</h2>
              <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 13.5, lineHeight: 1.55 }}>{detail}</p>
            </article>
          ))}
        </div>
        <Link
          href="/operator/upload"
          style={{ display: "inline-flex", alignItems: "center", height: 48, padding: "0 22px", marginTop: 24, borderRadius: 8, background: "#1E3A2C", color: "#F2EEE5", fontSize: 15, fontWeight: 600, textDecoration: "none" }}
        >
          Start an audit
        </Link>
      </div>
    </BellwetherShell>
  );
}
