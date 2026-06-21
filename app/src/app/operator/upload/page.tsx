import Link from "next/link";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF, monoPill } from "@/components/bellwether/brand";
import { getPilotSession } from "@/lib/auth/session";
import { listOperatorAuditSummaries, type OperatorAuditSummary } from "@/lib/audit/operator-audit-db";
import { uploadWorkbookAction } from "./actions";
import { UploadWorkbookForm } from "./UploadWorkbookForm";

// Frame 5 of the design — upload records. The dropzone hosts the real
// UploadWorkbookForm (live file upload → audit) and the "Recent uploads" table is
// wired to the operator's real audits. The auto column-mapping preview is the
// design's representative sample (no live column-mapping pipeline surfaced yet).

// The upload action runs parse + rule execution synchronously (no cron/queue worker), so the
// server function needs room to finish the full audit before returning.
export const maxDuration = 60;

const FORMATS = [".XLSX", ".CSV", "EDI 856", "GDSN", "PDF scan"];

const MAPPING = [
  { col: "PROD_DESC", kde: "Product description", state: "ok" as const },
  { col: "LOT_NO", kde: "Traceability lot code", state: "ok" as const },
  { col: "RCV_DATE", kde: "Receiving date", state: "ok" as const },
  { col: "— none —", kde: "TLC source", state: "unmapped" as const }
];

function formatFor(fileName: string): string {
  const ext = fileName.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "xlsx" || ext === "xls" || ext === "xlsm") return "Excel";
  if (ext === "csv") return "CSV";
  if (ext === "edi") return "EDI 856";
  if (ext === "pdf") return "PDF scan";
  if (ext === "xml") return "GDSN";
  return ext ? ext.toUpperCase() : "—";
}

function statusFor(a: OperatorAuditSummary): { label: string; color: string; bg: string } {
  const stage = (a.jobStatus ?? a.status ?? "").toLowerCase();
  if (["queued", "running", "processing", "pending"].includes(stage)) return { label: "Processing", color: "#8A5E0E", bg: "#F7ECCE" };
  if (a.readinessPassed) return { label: "Audited", color: "#1F5638", bg: "#DDEEE0" };
  return { label: "Review", color: "#8A5E0E", bg: "#F7ECCE" };
}

function shortDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

const card = { background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12 } as const;
const eyebrow = { fontFamily: MONO, fontSize: 10, letterSpacing: ".06em", color: "#9A9181", textTransform: "uppercase" } as const;
const arrowIcon = (
  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#9A9181" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);
const checkIcon = (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#1F5638" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" style={{ justifySelf: "end" }}>
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

export default async function UploadPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  const resolvedSearchParams = await searchParams;
  const session = await getPilotSession();
  const recent = session ? await listOperatorAuditSummaries(session, 5).catch(() => [] as OperatorAuditSummary[]) : [];

  return (
    <BellwetherShell
      active="upload"
      topbarLeft="UPLOAD RECORDS"
      topbarRight={
        <Link href="/operator/help" style={{ fontSize: 12.5, color: "#6E6757", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 7 }}>
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          How redaction works
        </Link>
      }
    >
      <div style={{ padding: 28 }}>
        <span style={eyebrow}>Upload records</span>
        <h2 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>Bring your records — any format.</h2>
        <p style={{ margin: "6px 0 0", color: "#6E6757", fontSize: 14, maxWidth: 620 }}>
          Drop a workbook or export and we&apos;ll auto-detect the layout, map your columns to FSMA 204 KDEs, and queue a readiness audit. Send redacted samples only.
        </p>

        {/* dropzone hosting the real uploader */}
        <div style={{ marginTop: 20, border: "1.5px dashed #C0B79F", borderRadius: 14, background: "#F4F0E6", padding: 32, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", gap: 12 }}>
          <span style={{ width: 58, height: 58, borderRadius: 14, background: "#E4EFE7", color: "#1E3A2C", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
            <svg viewBox="0 0 24 24" width="27" height="27" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 10l5-5 5 5M12 5v12" />
              <path d="M5 21h14" />
            </svg>
          </span>
          <strong style={{ fontSize: 18 }}>Drag and drop your records here</strong>
          {resolvedSearchParams?.error ? (
            <p style={{ margin: 0, padding: "8px 13px", borderRadius: 8, border: "1px solid #E7C9C0", background: "#F6E3DE", color: "#8F2D22", fontSize: 13 }}>{resolvedSearchParams.error}</p>
          ) : null}
          <div style={{ width: "100%", maxWidth: 460 }}>
            <UploadWorkbookForm action={uploadWorkbookAction} />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7, justifyContent: "center", marginTop: 2 }}>
            {FORMATS.map((f) => (
              <span key={f} style={{ fontFamily: MONO, fontSize: 11, color: "#454035", background: "#EFE9DC", border: "1px solid #D7CFBE", padding: "4px 10px", borderRadius: 6 }}>{f}</span>
            ))}
          </div>
          <small style={{ marginTop: 4, fontFamily: MONO, fontSize: 10, color: "#9A9181", letterSpacing: ".03em" }}>MAX 10 MB · REDACTED SAMPLES ONLY · NO PRODUCTION CREDENTIALS</small>
        </div>

        {/* auto column mapping preview (representative) */}
        <div style={{ ...card, marginTop: 14, overflow: "hidden" }}>
          <div style={{ padding: "18px 22px 13px" }}>
            <span style={eyebrow}>Auto column mapping · preview</span>
            <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Detected → KDE</h3>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto", gap: 12, alignItems: "center", padding: "9px 22px", background: "#F4F0E6", borderTop: "1px solid #E4DDCD", borderBottom: "1px solid #E4DDCD", fontFamily: MONO, fontSize: 9.5, letterSpacing: ".04em", color: "#9A9181", textTransform: "uppercase" }}>
            <span>Your column</span><span /><span>Mapped KDE</span><span style={{ textAlign: "right" }}>State</span>
          </div>
          {MAPPING.map((m, i) => (
            <div key={m.kde} style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto", gap: 12, alignItems: "center", padding: "11px 22px", borderBottom: i < MAPPING.length - 1 ? "1px solid #EDE7D8" : undefined }}>
              <span style={{ fontFamily: MONO, fontSize: 12, color: m.state === "unmapped" ? "#9A9181" : "#454035" }}>{m.col}</span>
              {arrowIcon}
              <span style={{ fontSize: 13, color: m.state === "unmapped" ? "#8F2D22" : "#1A1813", fontWeight: m.state === "unmapped" ? 600 : 400 }}>{m.kde}</span>
              {m.state === "unmapped" ? <span style={{ ...monoPill("#8F2D22", "#F6E3DE", "3px 8px"), justifySelf: "end", fontSize: 10 }}>UNMAPPED</span> : checkIcon}
            </div>
          ))}
        </div>

        {/* recent uploads (representative) */}
        <div style={{ ...card, marginTop: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 22px 12px" }}>
            <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Recent uploads</h3>
            <Link href="/operator/audits" style={{ fontSize: 12.5, color: "#1E3A2C", fontWeight: 600, textDecoration: "none" }}>View all →</Link>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1.6fr 0.9fr 1fr 0.8fr", gap: 14, alignItems: "center", padding: "10px 22px", background: "#F4F0E6", borderTop: "1px solid #E4DDCD", borderBottom: "1px solid #E4DDCD", fontFamily: MONO, fontSize: 9.5, letterSpacing: ".04em", color: "#9A9181", textTransform: "uppercase" }}>
            <span>File</span><span>Format</span><span>Uploaded</span><span style={{ textAlign: "right" }}>Status</span>
          </div>
          {recent.length === 0 ? (
            <div style={{ padding: "26px 22px", textAlign: "center", color: "#6E6757", fontSize: 13.5 }}>No uploads yet — drop a workbook above to run your first audit.</div>
          ) : (
            recent.map((a, i) => {
              const s = statusFor(a);
              return (
                <Link
                  key={a.auditId}
                  href={`/operator/audits/${a.auditId}`}
                  style={{ display: "grid", gridTemplateColumns: "1.6fr 0.9fr 1fr 0.8fr", gap: 14, alignItems: "center", padding: "12px 22px", borderBottom: i < recent.length - 1 ? "1px solid #EDE7D8" : undefined, textDecoration: "none", color: "#1A1813" }}
                >
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>{a.fileName}</span>
                  <span style={{ fontFamily: MONO, fontSize: 11, color: "#6E6757" }}>{formatFor(a.fileName)}</span>
                  <span style={{ fontSize: 12.5, color: "#6E6757" }}>{shortDate(a.createdAt)}</span>
                  <span style={{ ...monoPill(s.color, s.bg, "3px 9px"), justifySelf: "end", fontSize: 10.5 }}>{s.label}</span>
                </Link>
              );
            })
          )}
        </div>
      </div>
    </BellwetherShell>
  );
}
