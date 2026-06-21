import Link from "next/link";
import { redirect } from "next/navigation";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/roles";
import { listOperatorAuditSummaries, type OperatorAuditSummary } from "@/lib/audit/operator-audit-db";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF, monoPill } from "@/components/bellwether/brand";

// Frame 6 of the design — readiness reports. The report-history table is wired to
// the operator's real audits; the featured "latest report" headline numbers are the
// design's representative sample (no backing readiness-rollup pipeline yet).

function verdictFor(a: OperatorAuditSummary): { label: string; color: string; bg: string } {
  if (a.readinessPassed) return { label: "Ready", color: "#1F5638", bg: "#DDEEE0" };
  if (a.blockerCount > 0) return { label: "Not ready", color: "#8F2D22", bg: "#F6E3DE" };
  return { label: "At risk", color: "#8A5E0E", bg: "#F7ECCE" };
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

const downloadIcon = (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
  </svg>
);

export default async function ReportsPage() {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, "/operator/reports")) {
    redirect("/login/operator?auth=required&next=/operator/reports");
  }
  const audits = await listOperatorAuditSummaries(session).catch(() => [] as OperatorAuditSummary[]);
  const latest = audits[0];
  const totalFindings = audits.reduce((sum, a) => sum + a.findingsCount, 0);
  const anyNotReady = audits.some((a) => !a.readinessPassed);
  const verdictLabel = audits.length === 0 ? "Not yet ready" : anyNotReady ? "Not yet ready" : "On track";
  const verdictColor = anyNotReady || audits.length === 0 ? "#8F2D22" : "#1F5638";

  return (
    <BellwetherShell
      active="reports"
      topbarLeft="READINESS REPORTS"
      topbarRight={
        <button style={{ height: 38, padding: "0 16px", border: "1px solid #C9C1AF", borderRadius: 8, background: "#fff", color: "#1A1813", fontSize: 13.5, fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 8, fontFamily: "inherit" }}>
          {downloadIcon}
          Export all (PDF)
        </button>
      }
    >
      <div style={{ padding: 28 }}>
        <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Reports</span>
        <h2 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>Your readiness reports</h2>
        <p style={{ margin: "6px 0 0", color: "#6E6757", fontSize: 14 }}>
          The deliverable: a red / yellow / green verdict with a supplier scorecard and a citation-backed remediation plan.
        </p>

        {/* featured latest report */}
        <div style={{ marginTop: 20, border: "1px solid #E7C9C0", borderRadius: 14, background: "linear-gradient(135deg,#FBFAF5 0%,#F8E7E1 130%)", overflow: "hidden", display: "grid", gridTemplateColumns: "1.5fr 1fr" }}>
          <div style={{ padding: "26px 28px", borderRight: "1px solid #EAD7CF" }}>
            <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: ".06em", color: "#9A9181", textTransform: "uppercase" }}>
              {latest ? `Latest · generated ${formatDate(latest.createdAt)} · ${latest.auditId}` : "No reports generated yet"}
            </span>
            <h3 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 25, fontWeight: 600 }}>
              {session.companyName ?? "Your operation"} — readiness summary
            </h3>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginTop: 14 }}>
              <strong style={{ fontFamily: SERIF, fontSize: 22, fontWeight: 600, color: verdictColor }}>{verdictLabel}</strong>
              <span style={{ display: "flex", gap: 4 }}>
                <span style={{ width: 34, height: 6, borderRadius: 99, background: "#B0392B" }} />
                <span style={{ width: 18, height: 6, borderRadius: 99, background: "#C0851A" }} />
                <span style={{ width: 12, height: 6, borderRadius: 99, background: "#2E7A4E" }} />
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginTop: 20 }}>
              {[["On-FTL scope", "21", "/38", "#1A1813"], ["KDE gaps", String(totalFindings), "", "#8F2D22"], ["Blast radius", "18", "", "#8F2D22"]].map(([label, value, unit, color]) => (
                <div key={label}>
                  <span style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: ".05em", color: "#9A9181", textTransform: "uppercase" }}>{label}</span>
                  <strong style={{ display: "block", marginTop: 5, fontFamily: SERIF, fontSize: 22, fontWeight: 500, color }}>
                    {value}
                    {unit ? <span style={{ fontSize: 14, color: "#6E6757" }}>{unit}</span> : null}
                  </strong>
                </div>
              ))}
            </div>
          </div>
          <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", justifyContent: "center", gap: 10 }}>
            <a
              href={latest ? `/operator/audits/${latest.auditId}/artifacts/package` : "#"}
              style={{ height: 48, borderRadius: 8, background: "#1A1813", color: "#F2EEE5", fontSize: 14.5, fontWeight: 600, textDecoration: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 9 }}
            >
              {downloadIcon}
              Download PDF package
            </a>
            <Link
              href={latest ? `/operator/audits/${latest.auditId}/report` : "#"}
              style={{ height: 48, border: "1px solid #C9C1AF", borderRadius: 8, background: "#fff", color: "#1A1813", fontSize: 14.5, fontWeight: 600, textDecoration: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 9 }}
            >
              View full report
            </Link>
            <small style={{ fontFamily: MONO, fontSize: 10, color: "#9A9181", textAlign: "center", letterSpacing: ".02em", lineHeight: 1.5 }}>
              EVERY FINDING CITES AN eCFR / FTL RULE
            </small>
          </div>
        </div>

        {/* report history */}
        <div style={{ background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12, marginTop: 14, overflow: "hidden" }}>
          <div style={{ padding: "16px 22px 12px" }}>
            <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Report history</h3>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1.1fr 0.9fr auto", gap: 14, alignItems: "center", padding: "10px 22px", background: "#F4F0E6", borderTop: "1px solid #E4DDCD", borderBottom: "1px solid #E4DDCD", fontFamily: MONO, fontSize: 9.5, letterSpacing: ".04em", color: "#9A9181", textTransform: "uppercase" }}>
            <span>Report</span><span>Generated</span><span>Verdict</span><span>Findings</span><span style={{ textAlign: "right" }}>File</span>
          </div>
          {audits.length === 0 ? (
            <div style={{ padding: "32px 22px", textAlign: "center", color: "#6E6757", fontSize: 13.5 }}>
              No reports yet — run a readiness audit to generate one.
            </div>
          ) : (
            audits.map((a, i) => {
              const v = verdictFor(a);
              return (
                <div key={a.auditId} style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1.1fr 0.9fr auto", gap: 14, alignItems: "center", padding: "13px 22px", borderBottom: i < audits.length - 1 ? "1px solid #EDE7D8" : undefined }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13.5 }}>{a.fileName}</div>
                    <div style={{ fontFamily: MONO, fontSize: 10.5, color: "#9A9181" }}>{a.auditId}</div>
                  </div>
                  <span style={{ fontSize: 12.5, color: "#6E6757" }}>{formatDate(a.createdAt)}</span>
                  <span style={monoPill(v.color, v.bg, "3px 9px")}>{v.label}</span>
                  <span style={{ fontSize: 13, color: "#6E6757" }}>{a.findingsCount}</span>
                  <Link href={`/operator/audits/${a.auditId}/report`} style={{ justifySelf: "end", color: "#1E3A2C" }} aria-label={`Open report for ${a.fileName}`}>
                    {downloadIcon}
                  </Link>
                </div>
              );
            })
          )}
        </div>
      </div>
    </BellwetherShell>
  );
}
