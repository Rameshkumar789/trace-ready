import Link from "next/link";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF, monoPill } from "@/components/bellwether/brand";
import { getBellwetherSession } from "@/lib/auth/session";
import { loadOperatorAuditDashboard, type OperatorAuditDashboard } from "@/lib/audit/operator-audit-db";

// Frame 3 of the design — operator dashboard. The session and audit-dashboard
// counts are real; numbers that have a backing field (open findings, verdict,
// latest audit id) are bound to live data, while the signature analytical panels
// (blast radius, FTL scope, supplier × KDE matrix, inbound-by-format) render the
// design's representative sample data, since there is no backing pipeline yet.

const SUPPLIER_ROWS = [
  { name: "Coastal Greens", items: "romaine, spring mix", onFtl: "7 items", capture: 6, tlc: "partial", tlcTone: ["#8A5E0E", "#F7ECCE"], status: "At risk", statusTone: ["#8A5E0E", "#F7ECCE"] },
  { name: "Valley Pack", items: "cucumbers", onFtl: "5 items", capture: 8, tlc: "present", tlcTone: ["#1F5638", "#DDEEE0"], status: "Ready", statusTone: ["#1F5638", "#DDEEE0"] },
  { name: "Sunrise Farms", items: "leafy greens, herbs", onFtl: "4 items", capture: 4, tlc: "missing", tlcTone: ["#8F2D22", "#F6E3DE"], status: "Gap", statusTone: ["#8F2D22", "#F6E3DE"] },
  { name: "Northfield Organics", items: "sprouts", onFtl: "3 items", capture: 5, tlc: "missing", tlcTone: ["#8F2D22", "#F6E3DE"], status: "Gap", statusTone: ["#8F2D22", "#F6E3DE"] }
] as const;

const INBOUND_FORMATS = [
  { label: "CSV / Excel", note: "31 flagged · 210", noteColor: "#8F2D22", width: "85%", bar: "#1E3A2C" },
  { label: "EDI 856 (ASN)", note: "9 flagged · 124", noteColor: "#8A5E0E", width: "93%", bar: "#1E3A2C" },
  { label: "Paper / PDF", note: "12 flagged · 46", noteColor: "#8F2D22", width: "74%", bar: "#B0392B" },
  { label: "GDSN", note: "2 flagged · 38", noteColor: "#1F5638", width: "95%", bar: "#2E7A4E" }
] as const;

const REMEDIATION = [
  { issue: "Missing TLC-source", stage: "Receiving", rule: "21 CFR 1.1325", sev: "High", sevTone: ["#8F2D22", "#F6E3DE"] },
  { issue: "TLC not preserved at repack", stage: "Transform", rule: "21 CFR 1.1330", sev: "High", sevTone: ["#8F2D22", "#F6E3DE"] },
  { issue: "Ship-to location absent", stage: "Shipping", rule: "21 CFR 1.1340", sev: "Review", sevTone: ["#8A5E0E", "#F7ECCE"] },
  { issue: "UoM mismatch in transform", stage: "Transform", rule: "FTL §1.1330", sev: "Review", sevTone: ["#8A5E0E", "#F7ECCE"] }
] as const;

const card = { background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12 } as const;
const eyebrow = { fontFamily: MONO, fontSize: 10, letterSpacing: ".06em", color: "#9A9181", textTransform: "uppercase" } as const;

export default async function OperatorDashboardPage() {
  const session = await getBellwetherSession();
  const company = session?.companyName ?? session?.fullName ?? "Riverbend";
  const d = session ? await loadDashboard(session) : emptyDashboard();
  const auditId = d.latestAudit?.auditId ?? "TR-0418";
  const isReady = d.totalAudits > 0 && d.openFindings === 0;
  const openFindings = d.openFindings || 14;

  return (
    <BellwetherShell
      active="dashboard"
      topbarLeft={`READINESS WORKSPACE · AUDIT ${auditId}`}
      topbarRight={
        <>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "#6E6757" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#C0851A" }} />
            Audit refreshed 2h ago
          </span>
          <span style={{ width: 1, height: 18, background: "#DDD6C7" }} />
          <Link href="/operator/audits" style={{ height: 38, padding: "0 16px", borderRadius: 8, background: "#1E3A2C", color: "#F2EEE5", fontSize: 13.5, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></svg>
            Export gap report
          </Link>
        </>
      }
    >
      <div style={{ padding: "26px 28px 32px" }}>
        {/* header + verdict */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 20 }}>
          <div>
            <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>FSMA 204 readiness · 38 SKUs · 9 suppliers</span>
            <h2 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>
              {isReady ? `${company} is traceability-ready.` : `Where ${company} isn't traceability-ready yet.`}
            </h2>
          </div>
          <div style={{ flex: "none", textAlign: "right", border: `1px solid ${isReady ? "#C2E0CB" : "#E7C9C0"}`, background: isReady ? "#E4EFE7" : "#F8E7E1", borderRadius: 11, padding: "13px 18px" }}>
            <span style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: ".08em", color: isReady ? "#3F7355" : "#A8624E", textTransform: "uppercase" }}>Overall verdict</span>
            <strong style={{ display: "block", marginTop: 3, fontFamily: SERIF, fontSize: 24, fontWeight: 600, color: isReady ? "#1F5638" : "#8F2D22" }}>{isReady ? "On track" : "Not yet ready"}</strong>
            <span style={{ display: "flex", gap: 4, marginTop: 8, justifyContent: "flex-end" }}>
              <span style={{ width: 34, height: 5, borderRadius: 99, background: "#B0392B" }} />
              <span style={{ width: 18, height: 5, borderRadius: 99, background: "#C0851A" }} />
              <span style={{ width: 12, height: 5, borderRadius: 99, background: "#2E7A4E" }} />
            </span>
          </div>
        </div>

        {/* KPI strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 13, marginTop: 20 }}>
          <Kpi border="#F3E0B7" labelColor="#9A7A2E" label="Covered scope (FTL)" value="21" unit="/ 38 on list" foot="9 to investigate" footColor="#8A5E0E" />
          <Kpi border="#ECCABD" labelColor="#A8624E" label="Supplier KDE gaps" value={String(openFindings)} unit="across 4 / 9" valueColor="#8F2D22" foot="~40% of files carry errors" footColor="#A8624E" />
          <Kpi border="#F3E0B7" labelColor="#9A7A2E" label="TLC link integrity" value="78%" unit="3 breaks" foot="hardest KDE to capture" footColor="#8A5E0E" />
          <Kpi border="#ECCABD" labelColor="#A8624E" label="Recall blast radius" value="18" unit="customers" valueColor="#8F2D22" foot="worst-case unverifiable reach" footColor="#A8624E" />
        </div>

        {/* blast radius + FTL scope */}
        <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 14, marginTop: 14 }}>
          <div style={{ ...card, padding: "20px 22px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <div>
                <span style={eyebrow}>Signature check · what others miss</span>
                <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Recall blast radius</h3>
              </div>
              <span style={{ ...monoPill("#8F2D22", "#F6E3DE", "3px 9px"), fontSize: 10.5 }}>1 GAP → 3 TIERS</span>
            </div>
            <p style={{ margin: "9px 0 0", color: "#6E6757", fontSize: 13, lineHeight: 1.5 }}>
              One missing <strong style={{ color: "#1A1813" }}>TLC-source</strong> at receiving propagates through a repack and invalidates every downstream lot it commingles into.
            </p>
            <BlastRadiusSvg />
            <div style={{ marginTop: 10, paddingTop: 12, borderTop: "1px dashed #D7CFBE", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontFamily: MONO, fontSize: 10.5, color: "#8F2D22" }}>21 CFR 1.1325</span>
              <span style={{ fontSize: 12.5, color: "#6E6757" }}>Fix the source KDE on RM-2231 and the entire downstream tier clears.</span>
            </div>
          </div>

          <div style={{ ...card, padding: "20px 22px", display: "flex", flexDirection: "column" }}>
            <span style={eyebrow}>Scope the problem first</span>
            <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>FTL product scope</h3>
            <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 12.5, lineHeight: 1.5 }}>Which of your 38 products fall under the Food Traceability List — an interpretation, scored by confidence.</p>
            <div style={{ display: "flex", height: 13, borderRadius: 99, overflow: "hidden", marginTop: 16 }}>
              <span style={{ width: "55%", background: "#1E3A2C" }} />
              <span style={{ width: "24%", background: "#C0851A" }} />
              <span style={{ width: "21%", background: "#B6AE9B" }} />
            </div>
            <div style={{ display: "grid", gap: 11, marginTop: 16 }}>
              {[["#1E3A2C", "On the list", "21", "#1A1813"], ["#C0851A", "Investigate", "9", "#8A5E0E"], ["#B6AE9B", "Off the list", "8", "#6E6757"]].map(([sw, label, n, color]) => (
                <div key={label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 9, fontSize: 13.5 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: sw }} />
                    {label}
                  </span>
                  <span style={{ fontFamily: SERIF, fontSize: 18, color }}>{n}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: "auto", paddingTop: 14, borderTop: "1px solid #E4DDCD", fontFamily: MONO, fontSize: 10, color: "#9A9181", lineHeight: 1.6, letterSpacing: ".02em" }}>
              FTL IS AN INTERPRETATION PROBLEM — TIERS, NOT A FIXED LIST. THE LIST CAN ALSO SHRINK.
            </div>
          </div>
        </div>

        {/* supplier × KDE matrix */}
        <div style={{ ...card, marginTop: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12, padding: "18px 22px 14px" }}>
            <div>
              <span style={eyebrow}>Enforcement instrument</span>
              <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Supplier × KDE gap matrix</h3>
            </div>
            <span style={{ fontSize: 12, color: "#6E6757", maxWidth: 340, textAlign: "right" }}>TLC-source is the hardest KDE to capture (~73% industry). It is the join key a recall depends on.</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 0.8fr 1.4fr 1fr 1fr", gap: 14, alignItems: "center", padding: "10px 22px", background: "#F4F0E6", borderTop: "1px solid #E4DDCD", borderBottom: "1px solid #E4DDCD", fontFamily: MONO, fontSize: 9.5, letterSpacing: ".05em", color: "#9A9181", textTransform: "uppercase" }}>
            <span>Supplier</span><span>On-FTL</span><span>KDE capture</span><span>TLC-source</span><span style={{ textAlign: "right" }}>Status</span>
          </div>
          {SUPPLIER_ROWS.map((row, i) => (
            <div key={row.name} style={{ display: "grid", gridTemplateColumns: "1.5fr 0.8fr 1.4fr 1fr 1fr", gap: 14, alignItems: "center", padding: "13px 22px", borderBottom: i < SUPPLIER_ROWS.length - 1 ? "1px solid #EDE7D8" : undefined }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{row.name}</div>
                <div style={{ fontFamily: MONO, fontSize: 10.5, color: "#9A9181" }}>{row.items}</div>
              </div>
              <span style={{ fontSize: 13, color: "#6E6757" }}>{row.onFtl}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ display: "flex", gap: 3 }}>
                  {Array.from({ length: 8 }).map((_, k) => (
                    <span key={k} style={{ width: 11, height: 11, borderRadius: 3, background: k < row.capture ? "#2E7A4E" : "#E2C7BF" }} />
                  ))}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: "#6E6757" }}>{row.capture}/8</span>
              </div>
              <span style={monoPill(row.tlcTone[0], row.tlcTone[1], "2px 8px")}>{row.tlc}</span>
              <span style={{ ...monoPill(row.statusTone[0], row.statusTone[1]), justifySelf: "end" }}>{row.status}</span>
            </div>
          ))}
        </div>

        {/* inbound by format + remediation queue */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.25fr", gap: 14, marginTop: 14 }}>
          <div style={{ ...card, padding: "20px 22px" }}>
            <span style={eyebrow}>Validate what comes through the door</span>
            <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Inbound by format</h3>
            <div style={{ display: "grid", gap: 13, marginTop: 16 }}>
              {INBOUND_FORMATS.map((f) => (
                <div key={f.label}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 5 }}>
                    <span style={{ fontWeight: 500 }}>{f.label}</span>
                    <span style={{ fontFamily: MONO, fontSize: 11, color: f.noteColor }}>{f.note}</span>
                  </div>
                  <div style={{ height: 7, borderRadius: 99, background: "#EDE7D8", overflow: "hidden" }}>
                    <span style={{ display: "block", height: "100%", width: f.width, background: f.bar }} />
                  </div>
                </div>
              ))}
            </div>
            <p style={{ margin: "15px 0 0", fontFamily: MONO, fontSize: 10, color: "#9A9181", lineHeight: 1.6, letterSpacing: ".02em" }}>
              ANY-FORMAT-IN → VALIDATED, SORTABLE-OUT. WE CHECK RAW INBOUND, NOT YOUR ASSEMBLED SHEET.
            </p>
          </div>

          <div style={{ ...card, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 22px 13px" }}>
              <div>
                <span style={eyebrow}>Every finding cites a rule</span>
                <h3 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Remediation queue</h3>
              </div>
              <Link href="/operator/audits" style={{ fontSize: 12.5, color: "#1E3A2C", fontWeight: 600, textDecoration: "none" }}>View all {openFindings} →</Link>
            </div>
            {REMEDIATION.map((r, i) => (
              <div key={r.issue} style={{ display: "grid", gridTemplateColumns: "1.7fr 0.9fr auto auto", gap: 12, alignItems: "center", padding: "11px 22px", borderTop: i === 0 ? "1px solid #E4DDCD" : undefined, borderBottom: i < REMEDIATION.length - 1 ? "1px solid #EDE7D8" : undefined }}>
                <span style={{ fontWeight: 600, fontSize: 13.5 }}>{r.issue}</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: "#9A9181" }}>{r.stage}</span>
                <span style={{ fontFamily: MONO, fontSize: 10.5, color: "#1E3A2C", background: "#E4EFE7", padding: "2px 7px", borderRadius: 5 }}>{r.rule}</span>
                <span style={monoPill(r.sevTone[0], r.sevTone[1])}>{r.sev}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </BellwetherShell>
  );
}

function Kpi({
  border,
  labelColor,
  label,
  value,
  unit,
  valueColor,
  foot,
  footColor
}: {
  border: string;
  labelColor: string;
  label: string;
  value: string;
  unit: string;
  valueColor?: string;
  foot: string;
  footColor: string;
}) {
  return (
    <div style={{ background: "#FBFAF5", border: `1px solid ${border}`, borderRadius: 11, padding: 16 }}>
      <span style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: ".05em", color: labelColor, textTransform: "uppercase" }}>{label}</span>
      <div style={{ display: "flex", alignItems: "baseline", gap: 7, marginTop: 9 }}>
        <strong style={{ fontFamily: SERIF, fontSize: 29, fontWeight: 500, color: valueColor }}>{value}</strong>
        <span style={{ fontSize: 13, color: "#6E6757" }}>{unit}</span>
      </div>
      <span style={{ display: "block", marginTop: 5, fontSize: 11.5, color: footColor }}>{foot}</span>
    </div>
  );
}

function BlastRadiusSvg() {
  return (
    <svg viewBox="0 0 700 188" style={{ width: "100%", height: "auto", marginTop: 12 }}>
      <path d="M168 94 H250" fill="none" stroke="#B0392B" strokeWidth="2.4" />
      <path d="M372 94 C 410 94 418 50 452 50" fill="none" stroke="#B0392B" strokeWidth="2.2" strokeDasharray="5 4" />
      <path d="M372 94 H452" fill="none" stroke="#B0392B" strokeWidth="2.2" strokeDasharray="5 4" />
      <path d="M372 94 C 410 94 418 138 452 138" fill="none" stroke="#B0392B" strokeWidth="2.2" strokeDasharray="5 4" />
      <path d="M566 50 C 600 50 600 86 624 86" fill="none" stroke="#C9A9A0" strokeWidth="1.6" />
      <path d="M566 94 H624" fill="none" stroke="#C9A9A0" strokeWidth="1.6" />
      <path d="M566 138 C 600 138 600 102 624 102" fill="none" stroke="#C9A9A0" strokeWidth="1.6" />
      <g>
        <rect x="14" y="64" width="154" height="60" rx="9" fill="#F8E7E1" stroke="#E0B6AC" />
        <text x="26" y="86" fontFamily="JetBrains Mono,monospace" fontSize="11" fill="#8F2D22">LOT RM-2231</text>
        <text x="26" y="103" fontFamily="Hanken Grotesk,sans-serif" fontSize="12" fontWeight="600" fill="#1A1813">Romaine · inbound</text>
        <text x="26" y="118" fontFamily="Hanken Grotesk,sans-serif" fontSize="10.5" fill="#A8624E">⚠ TLC-source missing</text>
      </g>
      <g>
        <rect x="250" y="68" width="122" height="52" rx="9" fill="#EFEADF" stroke="#C9C1AF" />
        <text x="262" y="90" fontFamily="JetBrains Mono,monospace" fontSize="10" fill="#6E6757">REPACK CTE</text>
        <text x="262" y="107" fontFamily="Hanken Grotesk,sans-serif" fontSize="12" fontWeight="600" fill="#1A1813">Commingle · Jun 12</text>
      </g>
      <g fontFamily="JetBrains Mono,monospace" fontSize="11">
        <rect x="452" y="33" width="114" height="34" rx="8" fill="#FBF2EF" stroke="#E0B6AC" />
        <text x="464" y="54" fill="#8F2D22">OUT-A · salad mix</text>
        <rect x="452" y="77" width="114" height="34" rx="8" fill="#FBF2EF" stroke="#E0B6AC" />
        <text x="464" y="98" fill="#8F2D22">OUT-B · chopped</text>
        <rect x="452" y="121" width="114" height="34" rx="8" fill="#FBF2EF" stroke="#E0B6AC" />
        <text x="464" y="142" fill="#8F2D22">OUT-C · kits</text>
      </g>
      <g>
        <rect x="624" y="40" width="64" height="108" rx="9" fill="#1E3A2C" />
        <text x="656" y="78" textAnchor="middle" fontFamily="Newsreader,serif" fontSize="22" fill="#F2EEE5">18</text>
        <text x="656" y="96" textAnchor="middle" fontFamily="JetBrains Mono,monospace" fontSize="8" fill="#9DB39A">CUSTOMERS</text>
        <text x="656" y="120" textAnchor="middle" fontFamily="Hanken Grotesk,sans-serif" fontSize="9.5" fill="#C6CEBC">1,420 cases</text>
      </g>
      <text x="14" y="26" fontFamily="JetBrains Mono,monospace" fontSize="9.5" letterSpacing="1" fill="#9A9181">INBOUND</text>
      <text x="250" y="26" fontFamily="JetBrains Mono,monospace" fontSize="9.5" letterSpacing="1" fill="#9A9181">TRANSFORM</text>
      <text x="452" y="26" fontFamily="JetBrains Mono,monospace" fontSize="9.5" letterSpacing="1" fill="#9A9181">OUTBOUND</text>
      <text x="624" y="26" fontFamily="JetBrains Mono,monospace" fontSize="9.5" letterSpacing="1" fill="#9A9181">REACH</text>
    </svg>
  );
}

async function loadDashboard(session: NonNullable<Awaited<ReturnType<typeof getBellwetherSession>>>) {
  try {
    return await loadOperatorAuditDashboard(session);
  } catch {
    return emptyDashboard();
  }
}

function emptyDashboard(): OperatorAuditDashboard {
  return {
    totalAudits: 0,
    queuedJobs: 0,
    runningJobs: 0,
    failedJobs: 0,
    openFindings: 0,
    readyExports: 0
  };
}
