import type { ReactElement } from "react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF } from "@/components/bellwether/brand";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/roles";
import { listOperatorAuditSummaries, type OperatorAuditSummary } from "@/lib/audit/operator-audit-db";

// Frame 4 of the design — audits list. This screen maps cleanly onto real data:
// the stat cards and every table row are the operator's live audit summaries,
// rendered in the Bellwether table style with row links to /audits/{id}.

type StatusKind = "ready" | "action" | "processing";

function statusFor(a: OperatorAuditSummary): StatusKind {
  const stage = (a.jobStatus ?? a.status ?? "").toLowerCase();
  if (stage === "queued" || stage === "running" || stage === "processing" || stage === "pending") return "processing";
  return a.readinessPassed ? "ready" : "action";
}

const STATUS_STYLE: Record<StatusKind, { label: string; color: string; bg: string; icon: ReactElement }> = {
  action: {
    label: "Action needed",
    color: "#8F2D22",
    bg: "#F6E3DE",
    icon: (
      <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <path d="M10.3 3.2 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.2a2 2 0 0 0-3.4 0z" />
        <path d="M12 9v4" />
      </svg>
    )
  },
  ready: {
    label: "Ready",
    color: "#1F5638",
    bg: "#DDEEE0",
    icon: (
      <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    )
  },
  processing: {
    label: "Processing",
    color: "#8A5E0E",
    bg: "#F7ECCE",
    icon: (
      <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4" />
      </svg>
    )
  }
};

const COLS = "150px 1fr 120px 130px 110px 30px";

export default async function AuditsPage() {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, "/operator/audits")) {
    redirect("/login/operator?auth=required&next=/operator/audits");
  }
  const { auditRows, loadError } = await loadAuditRows(session);

  const openFindings = auditRows.reduce((sum, a) => sum + a.findingsCount, 0);
  const readyExports = auditRows.filter((a) => a.readinessPassed).length;

  return (
    <BellwetherShell
      active="audits"
      topbarLeft="AUDITS"
      topbarRight={
        <Link href="/operator/upload" style={{ height: 38, padding: "0 16px", borderRadius: 8, background: "#1E3A2C", color: "#F2EEE5", fontSize: 13.5, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10l5-5 5 5M12 5v12" /></svg>
          Upload records
        </Link>
      }
    >
      <div style={{ padding: 28 }}>
        <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Audits</span>
        <h2 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>Traceability readiness audits</h2>
        <p style={{ margin: "6px 0 0", color: "#6E6757", fontSize: 14 }}>Open an audit to resolve findings, review evidence, and export the readiness package.</p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 13, marginTop: 20 }}>
          <Stat border="#DDD6C7" labelColor="#9A9181" label="Total audits" value={auditRows.length} />
          <Stat border="#F0D9CF" labelColor="#A86A56" label="Open findings" value={openFindings} valueColor="#8F2D22" />
          <Stat border="#CFE6D7" labelColor="#3F7355" label="Ready exports" value={readyExports} valueColor="#1F5638" />
        </div>

        {loadError ? (
          <div style={{ marginTop: 18, background: "#F8E7E1", border: "1px solid #E7C9C0", borderRadius: 12, padding: "14px 18px" }}>
            <strong style={{ color: "#8F2D22", fontSize: 14 }}>Audit list unavailable</strong>
            <p style={{ margin: "4px 0 0", color: "#6E6757", fontSize: 13 }}>{loadError}</p>
          </div>
        ) : null}

        <div style={{ marginTop: 18, background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: COLS, gap: 14, alignItems: "center", padding: "13px 20px", background: "#F4F0E6", borderBottom: "1px solid #DDD6C7", fontFamily: MONO, fontSize: 10, letterSpacing: ".05em", color: "#9A9181", textTransform: "uppercase" }}>
            <span>Status</span><span>File</span><span>Created</span><span>Stage</span><span style={{ textAlign: "right" }}>Findings</span><span />
          </div>

          {auditRows.length === 0 ? (
            <div style={{ padding: "44px 20px", textAlign: "center" }}>
              <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>No uploaded audits yet</h3>
              <p style={{ margin: "6px 0 16px", color: "#6E6757", fontSize: 13.5 }}>Upload a workbook to create a database-backed audit job.</p>
              <Link href="/operator/upload" style={{ display: "inline-flex", alignItems: "center", gap: 8, height: 42, padding: "0 18px", borderRadius: 8, border: "1px solid #C9C1AF", background: "#fff", color: "#1A1813", fontSize: 14, fontWeight: 600, textDecoration: "none" }}>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10l5-5 5 5M12 5v12" /></svg>
                Upload records
              </Link>
            </div>
          ) : (
            auditRows.map((a, i) => {
              const kind = statusFor(a);
              const s = STATUS_STYLE[kind];
              const findings = kind === "processing" ? "—" : String(a.findingsCount);
              const blockerNote = kind === "processing" ? "pending" : `${a.blockerCount} blocker${a.blockerCount === 1 ? "" : "s"}`;
              return (
                <Link
                  key={a.auditId}
                  href={`/operator/audits/${a.auditId}`}
                  style={{ display: "grid", gridTemplateColumns: COLS, gap: 14, alignItems: "center", padding: "15px 20px", borderBottom: i < auditRows.length - 1 ? "1px solid #EDE7D8" : undefined, textDecoration: "none", color: "#1A1813" }}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, width: "fit-content", fontFamily: MONO, fontSize: 11, color: s.color, background: s.bg, padding: "3px 9px", borderRadius: 6 }}>
                    {s.icon}
                    {s.label}
                  </span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{a.fileName}</div>
                    <div style={{ fontFamily: MONO, fontSize: 11, color: "#9A9181" }}>{a.auditId}</div>
                  </div>
                  <span style={{ fontSize: 13, color: "#6E6757" }}>{formatDate(a.createdAt)}</span>
                  <span style={{ fontSize: 13, color: "#6E6757", textTransform: "capitalize" }}>{a.jobStatus ?? a.status}</span>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{findings}</div>
                    <div style={{ fontFamily: MONO, fontSize: 10.5, color: "#9A9181" }}>{blockerNote}</div>
                  </div>
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#9A9181" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
                </Link>
              );
            })
          )}
        </div>
      </div>
    </BellwetherShell>
  );
}

function Stat({ border, labelColor, label, value, valueColor }: { border: string; labelColor: string; label: string; value: number; valueColor?: string }) {
  return (
    <div style={{ background: "#FBFAF5", border: `1px solid ${border}`, borderRadius: 11, padding: 16 }}>
      <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: ".05em", color: labelColor, textTransform: "uppercase" }}>{label}</span>
      <strong style={{ display: "block", marginTop: 8, fontFamily: SERIF, fontSize: 26, fontWeight: 500, color: valueColor }}>{value}</strong>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

async function loadAuditRows(session: NonNullable<Awaited<ReturnType<typeof getPilotSession>>>): Promise<{
  auditRows: OperatorAuditSummary[];
  loadError?: string;
}> {
  try {
    return { auditRows: await listOperatorAuditSummaries(session) };
  } catch (error) {
    return {
      auditRows: [],
      loadError: error instanceof Error ? error.message : "Unable to read audit projects from Supabase."
    };
  }
}
