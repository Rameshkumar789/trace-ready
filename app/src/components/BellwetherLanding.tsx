"use client";

import { useState } from "react";
import type { CSSProperties } from "react";

// Ported faithfully from the Claude Design project "Bellwether main page"
// (file: Bellwether Landing.dc.html). Inline styles, palette, and fonts are
// preserved 1:1. The `<sc-if>` conditional blocks and the DCLogic form state
// class are reimplemented with React state below.

// Design props (originally `showReportArtifact` / `requestFormEnabled`, both
// defaulting to true). Flip these to toggle the hero report card / the form.
const SHOW_REPORT_ARTIFACT = true;
const REQUEST_FORM_ENABLED = true;

const MONO = "'JetBrains Mono',monospace";
const SERIF = "'Newsreader',serif";
const SANS = "'Hanken Grotesk',ui-sans-serif,system-ui,sans-serif";

const monoTag = (color: string, bg: string): CSSProperties => ({
  fontFamily: MONO,
  fontSize: 11,
  color,
  background: bg,
  padding: "2px 8px",
  borderRadius: 5
});

const dot = (background: string): CSSProperties => ({
  width: 9,
  height: 9,
  borderRadius: "50%",
  background
});

const inputStyle: CSSProperties = {
  height: 44,
  border: "1px solid #D7CFBE",
  borderRadius: 8,
  padding: "0 12px",
  fontSize: 14,
  fontFamily: SANS,
  color: "#1A1813",
  background: "#fff"
};

const labelStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  fontFamily: MONO,
  fontSize: 10.5,
  letterSpacing: ".05em",
  color: "#6E6757",
  textTransform: "uppercase"
};

const navLink: CSSProperties = {
  color: "#454035",
  fontSize: 14.5,
  fontWeight: 500,
  textDecoration: "none"
};

const Logo = ({ size = 42 }: { size?: number }) => (
  <svg viewBox="0 0 44 44" style={{ width: size, height: size, display: "block" }}>
    <rect x="1" y="1" width="42" height="42" rx="11" fill="#1E3A2C" />
    <g
      transform="translate(10 10)"
      fill="none"
      stroke="#EFEADF"
      strokeWidth="2.1"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.5 20.2a2.1 2.1 0 0 1-3 0" />
    </g>
    <circle cx="22" cy="11.6" r="2.2" fill="#37C07D" />
  </svg>
);

const checkRows: Array<{ n: string; title: string; copy: string; dot: string }> = [
  {
    n: "01",
    title: "Covered product scope",
    copy:
      "Which of your products appear to fall under the FDA Food Traceability List — on, off, or investigate.",
    dot: "#B0392B"
  },
  {
    n: "02",
    title: "Supplier KDE flow",
    copy:
      "Which suppliers must provide traceability information, and exactly what is missing today.",
    dot: "#B0392B"
  },
  {
    n: "03",
    title: "Lot-code lineage",
    copy: "Are incoming traceability lot codes preserved unless a real transformation occurs?",
    dot: "#C0851A"
  },
  {
    n: "04",
    title: "Transformation linkage",
    copy:
      "Are input lots connected to output lots during repacking, processing, or transformation?",
    dot: "#C0851A"
  },
  {
    n: "05",
    title: "Data-sharing readiness",
    copy: "Can you produce customer- and FDA-ready traceability records within 24 hours when asked?",
    dot: "#2E7A4E"
  },
  {
    n: "06",
    title: "Remediation plan",
    copy: "A prioritized checklist of what your team, suppliers, or systems should fix first.",
    dot: "#1E3A2C"
  }
];

const reportRows: Array<{ dot: string; label: string; tag: string; color: string; bg: string }> = [
  { dot: "#B0392B", label: "Covered product scope", tag: "REVIEW", color: "#8F2D22", bg: "#F6E3DE" },
  { dot: "#B0392B", label: "Supplier KDE flow", tag: "14 GAPS", color: "#8F2D22", bg: "#F6E3DE" },
  { dot: "#B0392B", label: "Lot-code lineage", tag: "3 BREAKS", color: "#8F2D22", bg: "#F6E3DE" },
  { dot: "#C0851A", label: "Transformation linkage", tag: "PARTIAL", color: "#8A5E0E", bg: "#F7ECCE" },
  { dot: "#C0851A", label: "Data-sharing readiness", tag: "SLOW", color: "#8A5E0E", bg: "#F7ECCE" },
  { dot: "#2E7A4E", label: "Recordkeeping baseline", tag: "READY", color: "#1F5638", bg: "#DDEEE0" }
];

const scorecardRows: Array<{ name: string; kde: string; tag: string; color: string; bg: string }> = [
  { name: "Coastal Greens LLC", kde: "KDE 6/8", tag: "AT RISK", color: "#8F2D22", bg: "#F6E3DE" },
  { name: "Valley Pack Inc.", kde: "KDE 8/8", tag: "READY", color: "#1F5638", bg: "#DDEEE0" },
  { name: "Sunrise Farms", kde: "KDE 4/8", tag: "AT RISK", color: "#8F2D22", bg: "#F6E3DE" },
  { name: "Harbor Distributing", kde: "KDE 7/8", tag: "PARTIAL", color: "#8A5E0E", bg: "#F7ECCE" }
];

const howSteps: Array<{ n: string; title: string; copy: string }> = [
  {
    n: "1",
    title: "Send sample records",
    copy:
      "Share redacted item lists, supplier lists, receiving/shipping samples, invoices, BOLs, ASNs, labels, or transformation records."
  },
  {
    n: "2",
    title: "We run Bellwether Audit",
    copy:
      "We review covered scope, KDE completeness, supplier gaps, lot-code lineage, transformation linkage, and data-sharing readiness."
  },
  {
    n: "3",
    title: "Receive a clear gap report",
    copy:
      "A red / yellow / green readiness report, a supplier scorecard, and a prioritized remediation checklist."
  },
  {
    n: "4",
    title: "Decide what to fix next",
    copy:
      "Fix internally, work with consultants, onboard a platform, or use Bellwether Remediation for recurring gaps."
  }
];

const icpTags = ["DISTRIBUTORS", "PACKERS", "REPACKERS", "FOOD HUBS", "FRESH-FOOD OPS"];

const partnerBullets: Array<{ color: string; text: string }> = [
  { color: "#1E3A2C", text: "Surface dirty supplier data before onboarding" },
  { color: "#5FB98E", text: "Neutral, citation-backed readiness scoring" },
  { color: "#D9A92E", text: "Hand off a clean dataset to any platform" }
];

const requestChecks = [
  "Red / yellow / green readiness report",
  "Supplier scorecard & remediation checklist",
  "Every finding linked to a record and a rule"
];

type FormState = {
  name: string;
  company: string;
  email: string;
  type: string;
  systems: string;
  concern: string;
};

const emptyForm: FormState = {
  name: "",
  company: "",
  email: "",
  type: "",
  systems: "",
  concern: ""
};

export default function BellwetherLanding() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);

  const set = (key: keyof FormState) => (e: { target: { value: string } }) =>
    setForm((s) => ({ ...s, [key]: e.target.value }));

  const trimmedName = form.name.trim();
  const thanksName = trimmedName ? ", " + trimmedName.split(" ")[0] : "";

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#EFEADF",
        color: "#1A1813",
        fontFamily: SANS
      }}
    >
      {/* Fonts + global keyframes / smoothing, ported from the design's <helmet> */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <style>{`
        html { scroll-behavior: smooth; }
        body { margin: 0; -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; background:#EFEADF; }
        @keyframes tr-blink { 0%,100% { opacity:1; } 50% { opacity:.25; } }
        ::selection { background:#1E3A2C; color:#F2EEE5; }
      `}</style>

      {/* TOP BAR */}
      <div style={{ background: "#1E3A2C", color: "#E9E4D6" }}>
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 18,
            padding: "8px 28px",
            fontFamily: MONO,
            fontSize: 11.5,
            letterSpacing: ".04em"
          }}
        >
          <span style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "#D9A92E",
                animation: "tr-blink 2.6s ease-in-out infinite"
              }}
            />
            FSMA 204 · COMPLIANCE DATE JUL 20 2028
          </span>
          <span style={{ color: "#A8B5A0" }}>AI-NATIVE TRACEABILITY READINESS &amp; REMEDIATION</span>
        </div>
      </div>

      {/* NAV */}
      <nav
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
          padding: "22px 28px"
        }}
      >
        <a
          href="#top"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            textDecoration: "none",
            color: "#1A1813"
          }}
        >
          <span style={{ display: "inline-flex", width: 42, height: 42 }}>
            <Logo />
          </span>
          <span style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
            <strong
              style={{
                fontFamily: SERIF,
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: "-.01em"
              }}
            >
              Bellwether
            </strong>
            <small
              style={{
                marginTop: 4,
                fontFamily: MONO,
                color: "#6E6757",
                fontSize: 10,
                letterSpacing: ".08em"
              }}
            >
              AUDIT · REMEDIATION
            </small>
          </span>
        </a>
        <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
          <a href="#check" style={navLink}>
            What we check
          </a>
          <a href="#report" style={navLink}>
            Sample report
          </a>
          <a href="#how" style={navLink}>
            How it works
          </a>
          <a href="#partners" style={navLink}>
            Partners
          </a>
        </div>
        <a
          href="#request"
          style={{
            display: "inline-flex",
            alignItems: "center",
            height: 44,
            padding: "0 20px",
            borderRadius: 8,
            background: "#1A1813",
            color: "#F2EEE5",
            fontSize: 14,
            fontWeight: 600,
            textDecoration: "none"
          }}
        >
          Request a sample audit
        </a>
      </nav>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 28px" }}>
        <div style={{ height: 1, background: "#DDD6C7" }} />
      </div>

      {/* HERO */}
      <header
        id="top"
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "minmax(0,1.05fr) minmax(420px,0.95fr)",
          gap: 56,
          alignItems: "start",
          padding: "58px 28px 36px"
        }}
      >
        <div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 9,
              fontFamily: MONO,
              fontSize: 11.5,
              letterSpacing: ".1em",
              color: "#6E6757",
              textTransform: "uppercase"
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#37C07D" }} />
            The FSMA 204 readiness audit
          </span>
          <h1
            style={{
              margin: "20px 0 0",
              fontFamily: SERIF,
              fontSize: 62,
              lineHeight: 1.02,
              fontWeight: 500,
              letterSpacing: "-.02em",
              maxWidth: 660
            }}
          >
            Find every traceability gap before an audit, recall, or onboarding does.
          </h1>
          <p
            style={{
              margin: "24px 0 0",
              maxWidth: 520,
              color: "#4A4537",
              fontSize: 18.5,
              lineHeight: 1.62
            }}
          >
            Bellwether Audit reviews your products, suppliers, shipment records, lot-code workflows,
            and transformation data — then shows precisely where your current process is{" "}
            <em style={{ fontStyle: "italic", fontFamily: SERIF }}>not yet</em> traceability-ready.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 32 }}>
            <a
              href="#request"
              style={{
                display: "inline-flex",
                alignItems: "center",
                height: 52,
                padding: "0 24px",
                borderRadius: 8,
                background: "#1E3A2C",
                color: "#F2EEE5",
                fontSize: 16,
                fontWeight: 600,
                textDecoration: "none"
              }}
            >
              Request a sample audit
            </a>
            <a
              href="#check"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                height: 52,
                padding: "0 22px",
                borderRadius: 8,
                background: "transparent",
                color: "#1A1813",
                fontSize: 16,
                fontWeight: 600,
                textDecoration: "none",
                border: "1px solid #C9C1AF"
              }}
            >
              See what we check
              <span style={{ fontFamily: MONO }}>→</span>
            </a>
          </div>
          <div style={{ display: "flex", gap: 0, marginTop: 40, borderTop: "1px solid #DDD6C7" }}>
            <div style={{ flex: 1, padding: "18px 18px 0 0" }}>
              <strong style={{ display: "block", fontFamily: SERIF, fontSize: 30, fontWeight: 500 }}>
                ~40%
              </strong>
              <span style={{ display: "block", marginTop: 4, color: "#6E6757", fontSize: 13, lineHeight: 1.4 }}>
                of supplier files carry KDE errors
              </span>
            </div>
            <div style={{ flex: 1, padding: "18px 18px 0 18px", borderLeft: "1px solid #DDD6C7" }}>
              <strong style={{ display: "block", fontFamily: SERIF, fontSize: 30, fontWeight: 500 }}>
                24 hrs
              </strong>
              <span style={{ display: "block", marginTop: 4, color: "#6E6757", fontSize: 13, lineHeight: 1.4 }}>
                to produce records when FDA asks
              </span>
            </div>
            <div style={{ flex: 1, padding: "18px 0 0 18px", borderLeft: "1px solid #DDD6C7" }}>
              <strong style={{ display: "block", fontFamily: SERIF, fontSize: 30, fontWeight: 500 }}>
                6
              </strong>
              <span style={{ display: "block", marginTop: 4, color: "#6E6757", fontSize: 13, lineHeight: 1.4 }}>
                dimensions of readiness checked
              </span>
            </div>
          </div>
        </div>

        {SHOW_REPORT_ARTIFACT && (
          <div
            style={{
              border: "1px solid #D7CFBE",
              borderRadius: 12,
              background: "#FBFAF5",
              boxShadow: "0 26px 70px rgba(40,36,24,.14)",
              overflow: "hidden"
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 10,
                padding: "14px 20px",
                background: "#1E3A2C",
                color: "#E9E4D6",
                fontFamily: MONO,
                fontSize: 11,
                letterSpacing: ".06em"
              }}
            >
              <span>BELLWETHER AUDIT — READINESS SUMMARY</span>
              <span style={{ color: "#A8B5A0" }}>TR-0418</span>
            </div>
            <div style={{ padding: 22 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 14 }}>
                <div>
                  <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181" }}>
                    OPERATOR
                  </span>
                  <h2 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 23, fontWeight: 600 }}>
                    Riverbend Produce Co.
                  </h2>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181" }}>
                    VERDICT
                  </span>
                  <strong
                    style={{
                      display: "block",
                      marginTop: 4,
                      fontFamily: SERIF,
                      fontSize: 21,
                      fontWeight: 600,
                      color: "#8F2D22"
                    }}
                  >
                    Not yet ready
                  </strong>
                </div>
              </div>

              {/* readiness meter */}
              <div style={{ display: "flex", gap: 5, marginTop: 18 }}>
                <span style={{ flex: 2, height: 8, borderRadius: 999, background: "#B0392B" }} />
                <span style={{ flex: 1, height: 8, borderRadius: 999, background: "#C0851A" }} />
                <span style={{ flex: 1, height: 8, borderRadius: 999, background: "#C0851A" }} />
                <span style={{ flex: 2, height: 8, borderRadius: 999, background: "#2E7A4E" }} />
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 7,
                  fontFamily: MONO,
                  fontSize: 10,
                  letterSpacing: ".04em",
                  color: "#9A9181"
                }}
              >
                <span>3 CRITICAL</span>
                <span>2 AT RISK</span>
                <span>1 READY</span>
              </div>

              {/* dimension rows */}
              <div
                style={{
                  marginTop: 18,
                  border: "1px solid #E4DDCD",
                  borderRadius: 9,
                  overflow: "hidden"
                }}
              >
                {reportRows.map((row, i) => (
                  <div
                    key={row.label}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "auto 1fr auto",
                      gap: 12,
                      alignItems: "center",
                      padding: "11px 14px",
                      borderBottom: i < reportRows.length - 1 ? "1px solid #EDE7D8" : undefined
                    }}
                  >
                    <span style={dot(row.dot)} />
                    <span style={{ fontSize: 13.5, fontWeight: 500 }}>{row.label}</span>
                    <span style={monoTag(row.color, row.bg)}>{row.tag}</span>
                  </div>
                ))}
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  marginTop: 16,
                  paddingTop: 15,
                  borderTop: "1px dashed #D7CFBE"
                }}
              >
                <span style={{ fontFamily: MONO, fontSize: 10.5, color: "#9A9181", letterSpacing: ".04em" }}>
                  426 RECORDS · 9 SUPPLIERS · 4 CTEs
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 7,
                    fontSize: 12.5,
                    fontWeight: 600,
                    color: "#1E3A2C"
                  }}
                >
                  Full report &amp; remediation plan
                  <span style={{ fontFamily: MONO }}>↗</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* POSITIONING */}
      <section style={{ background: "#1E3A2C", color: "#EBE6D8", marginTop: 48 }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "60px 28px" }}>
          <div style={{ paddingBottom: 14, borderBottom: "1px solid rgba(255,255,255,.16)" }}>
            <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#9DB39A", textTransform: "uppercase" }}>
              01 / The gap
            </span>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
              gap: 56,
              alignItems: "start",
              paddingTop: 40
            }}
          >
            <h2 style={{ margin: 0, fontFamily: SERIF, fontSize: 42, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-.015em" }}>
              Inside-the-walls traceability is not always FSMA 204 readiness.
            </h2>
            <div>
              <p style={{ margin: 0, color: "#C6CEBC", fontSize: 18, lineHeight: 1.65 }}>
                Your ERP or warehouse process may know what came in and what went out. But FSMA 204
                readiness also depends on supplier KDEs, traceability lot-code preservation,
                transformation linkage, downstream sharing, and audit-ready records.
              </p>
              <p
                style={{
                  margin: "18px 0 0",
                  color: "#EBE6D8",
                  fontSize: 18,
                  lineHeight: 1.65,
                  fontFamily: SERIF,
                  fontStyle: "italic"
                }}
              >
                Bellwether helps you see the gaps before they become implementation, audit, or recall
                problems.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* WHAT WE CHECK — ledger */}
      <section id="check" style={{ maxWidth: 1200, margin: "0 auto", padding: "76px 28px 0" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,.42fr) minmax(0,.58fr)",
            gap: 56,
            alignItems: "start"
          }}
        >
          <div style={{ position: "sticky", top: 24 }}>
            <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#6E6757", textTransform: "uppercase" }}>
              02 / What we check
            </span>
            <h2 style={{ margin: "14px 0 0", fontFamily: SERIF, fontSize: 40, lineHeight: 1.08, fontWeight: 500, letterSpacing: "-.015em" }}>
              Six dimensions of traceability readiness.
            </h2>
            <p style={{ margin: "18px 0 0", maxWidth: 380, color: "#4A4537", fontSize: 16, lineHeight: 1.6 }}>
              Every finding is linked to a specific record and a citation-backed rule — so you can
              act, not guess.
            </p>
          </div>
          <div>
            <div style={{ borderTop: "1px solid #1A1813" }}>
              {checkRows.map((row) => (
                <div
                  key={row.n}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr auto",
                    gap: 22,
                    alignItems: "baseline",
                    padding: "24px 4px",
                    borderBottom: "1px solid #DDD6C7"
                  }}
                >
                  <span style={{ fontFamily: MONO, fontSize: 13, color: "#9A9181" }}>{row.n}</span>
                  <div>
                    <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 23, fontWeight: 500 }}>{row.title}</h3>
                    <p style={{ margin: "7px 0 0", color: "#6E6757", fontSize: 15, lineHeight: 1.55, maxWidth: 440 }}>
                      {row.copy}
                    </p>
                  </div>
                  <span style={{ width: 11, height: 11, borderRadius: "50%", background: row.dot, marginTop: 8 }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" style={{ maxWidth: 1200, margin: "0 auto", padding: "76px 28px 0" }}>
        <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#6E6757", textTransform: "uppercase" }}>
          03 / How it works
        </span>
        <h2
          style={{
            margin: "14px 0 0",
            fontFamily: SERIF,
            fontSize: 40,
            lineHeight: 1.08,
            fontWeight: 500,
            letterSpacing: "-.015em",
            maxWidth: 560
          }}
        >
          From sample records to a clear gap report.
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4,minmax(0,1fr))",
            gap: 0,
            marginTop: 36,
            borderTop: "1px solid #1A1813"
          }}
        >
          {howSteps.map((step, i) => (
            <div
              key={step.n}
              style={{
                padding:
                  i === 0
                    ? "26px 22px 30px 0"
                    : i === howSteps.length - 1
                    ? "26px 0 30px 22px"
                    : "26px 22px 30px",
                borderRight: i < howSteps.length - 1 ? "1px solid #DDD6C7" : undefined
              }}
            >
              <span style={{ fontFamily: SERIF, fontSize: 40, fontWeight: 500, color: "#1E3A2C" }}>{step.n}</span>
              <h3 style={{ margin: "14px 0 9px", fontSize: 17, fontWeight: 600 }}>{step.title}</h3>
              <p style={{ margin: 0, color: "#6E6757", fontSize: 14, lineHeight: 1.55 }}>{step.copy}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SAMPLE REPORT + ICP band */}
      <section id="report" style={{ maxWidth: 1200, margin: "0 auto", padding: "76px 28px 0" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
            gap: 56,
            alignItems: "center"
          }}
        >
          <div>
            <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#6E6757", textTransform: "uppercase" }}>
              04 / Built first for
            </span>
            <h2 style={{ margin: "14px 0 0", fontFamily: SERIF, fontSize: 38, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-.015em" }}>
              Produce operators with fast-moving records.
            </h2>
            <p style={{ margin: "18px 0 0", color: "#4A4537", fontSize: 17, lineHeight: 1.62, maxWidth: 480 }}>
              We start with produce distributors, packers, repackers, food hubs, and fresh-food
              operators — where records move through invoices, BOLs, ASNs, labels, spreadsheets, and
              ERP/WMS exports.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 24 }}>
              {icpTags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontFamily: MONO,
                    padding: "7px 12px",
                    border: "1px solid #C9C1AF",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#454035"
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <div
            style={{
              border: "1px solid #D7CFBE",
              borderRadius: 12,
              background: "#FBFAF5",
              padding: 24,
              boxShadow: "0 14px 40px rgba(40,36,24,.07)"
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontFamily: MONO,
                fontSize: 10.5,
                letterSpacing: ".06em",
                color: "#9A9181",
                paddingBottom: 14,
                borderBottom: "1px solid #E4DDCD"
              }}
            >
              <span>SUPPLIER SCORECARD — EXCERPT</span>
              <span>TR-0418</span>
            </div>
            {scorecardRows.map((row, i) => (
              <div
                key={row.name}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto auto",
                  gap: 12,
                  alignItems: "center",
                  padding: "13px 0",
                  borderBottom: i < scorecardRows.length - 1 ? "1px solid #EDE7D8" : undefined
                }}
              >
                <span style={{ fontSize: 14, fontWeight: 500 }}>{row.name}</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: "#6E6757" }}>{row.kde}</span>
                <span style={monoTag(row.color, row.bg)}>{row.tag}</span>
              </div>
            ))}
            <p style={{ margin: "16px 0 0", fontFamily: MONO, fontSize: 10.5, color: "#9A9181", lineHeight: 1.5 }}>
              EACH FINDING LINKS TO A SOURCE RECORD AND AN eCFR / FTL RULE CITATION.
            </p>
          </div>
        </div>
      </section>

      {/* PARTNERS */}
      <section id="partners" style={{ maxWidth: 1200, margin: "0 auto", padding: "76px 28px 0" }}>
        <div
          style={{
            border: "1px solid #D7CFBE",
            borderRadius: 14,
            background: "#FBFAF5",
            padding: 40,
            display: "grid",
            gridTemplateColumns: "minmax(0,1.15fr) minmax(0,1fr)",
            gap: 48,
            alignItems: "center"
          }}
        >
          <div>
            <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#6E6757", textTransform: "uppercase" }}>
              05 / For partners
            </span>
            <h2 style={{ margin: "14px 0 0", fontFamily: SERIF, fontSize: 32, lineHeight: 1.12, fontWeight: 500, letterSpacing: "-.015em" }}>
              Designed to complement traceability platforms — not replace them.
            </h2>
            <p style={{ margin: "16px 0 0", color: "#4A4537", fontSize: 16.5, lineHeight: 1.62, maxWidth: 540 }}>
              For platforms, auditors, consultants, and ERP implementers, Bellwether acts as a
              pre-onboarding readiness scan — so supplier data is clean before migration begins.
            </p>
          </div>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 14 }}>
            {partnerBullets.map((b) => (
              <li key={b.text} style={{ position: "relative", paddingLeft: 24, fontSize: 15.5, lineHeight: 1.5 }}>
                <span style={{ position: "absolute", left: 0, top: 7, width: 9, height: 9, borderRadius: "50%", background: b.color }} />
                {b.text}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* REQUEST */}
      <section id="request" style={{ background: "#1E3A2C", color: "#EBE6D8", marginTop: 76 }}>
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "72px 28px",
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
            gap: 56,
            alignItems: "start"
          }}
        >
          <div>
            <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: "#9DB39A", textTransform: "uppercase" }}>
              06 / Request a sample audit
            </span>
            <h2 style={{ margin: "14px 0 0", fontFamily: SERIF, fontSize: 42, lineHeight: 1.06, fontWeight: 500, letterSpacing: "-.02em" }}>
              Want to know if your records are traceability-ready?
            </h2>
            <p style={{ margin: "20px 0 0", maxWidth: 460, color: "#C6CEBC", fontSize: 17.5, lineHeight: 1.62 }}>
              Send five redacted records. We&apos;ll run a Bellwether Audit and walk you through
              exactly where the gaps are — no platform migration required.
            </p>
            <div style={{ display: "grid", gap: 13, marginTop: 28 }}>
              {requestChecks.map((c) => (
                <div key={c} style={{ display: "flex", alignItems: "center", gap: 11, fontSize: 15 }}>
                  <span style={{ fontFamily: MONO, color: "#5FB98E" }}>✓</span>
                  {c}
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: "#FBFAF5", color: "#1A1813", borderRadius: 14, padding: 28 }}>
            {REQUEST_FORM_ENABLED ? (
              !submitted ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setSubmitted(true);
                  }}
                  style={{ display: "grid", gap: 14 }}
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <label style={labelStyle}>
                      Name
                      <input
                        value={form.name}
                        onChange={set("name")}
                        placeholder="Jane Doe"
                        style={inputStyle}
                      />
                    </label>
                    <label style={labelStyle}>
                      Company
                      <input
                        value={form.company}
                        onChange={set("company")}
                        placeholder="Acme Produce"
                        style={inputStyle}
                      />
                    </label>
                  </div>
                  <label style={labelStyle}>
                    Work email
                    <input
                      type="email"
                      value={form.email}
                      onChange={set("email")}
                      placeholder="jane@acme.com"
                      style={inputStyle}
                    />
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <label style={labelStyle}>
                      Company type
                      <select
                        value={form.type}
                        onChange={set("type")}
                        style={{ ...inputStyle, padding: "0 10px" }}
                      >
                        <option value="">Select…</option>
                        <option>Distributor</option>
                        <option>Packer / repacker</option>
                        <option>Food hub</option>
                        <option>Fresh-food operator</option>
                        <option>Platform / consultant</option>
                      </select>
                    </label>
                    <label style={labelStyle}>
                      Current systems
                      <input
                        value={form.systems}
                        onChange={set("systems")}
                        placeholder="ERP / WMS / sheets"
                        style={inputStyle}
                      />
                    </label>
                  </div>
                  <label style={labelStyle}>
                    Biggest concern
                    <textarea
                      value={form.concern}
                      onChange={set("concern")}
                      rows={2}
                      placeholder="e.g. supplier KDEs, lot-code lineage, an upcoming retailer mandate…"
                      style={{
                        border: "1px solid #D7CFBE",
                        borderRadius: 8,
                        padding: "10px 12px",
                        fontSize: 14,
                        color: "#1A1813",
                        background: "#fff",
                        resize: "vertical",
                        fontFamily: SANS
                      }}
                    />
                  </label>
                  <button
                    type="submit"
                    style={{
                      height: 50,
                      border: "none",
                      borderRadius: 8,
                      background: "#1A1813",
                      color: "#F2EEE5",
                      fontSize: 15,
                      fontWeight: 600,
                      cursor: "pointer",
                      fontFamily: SANS
                    }}
                  >
                    Request a 5-record sample audit
                  </button>
                  <small
                    style={{
                      fontFamily: MONO,
                      color: "#9A9181",
                      fontSize: 10,
                      lineHeight: 1.5,
                      textAlign: "center",
                      letterSpacing: ".03em"
                    }}
                  >
                    REDACTED SAMPLES ONLY · NEVER PRODUCTION CREDENTIALS
                  </small>
                </form>
              ) : (
                <div style={{ display: "grid", placeItems: "center", textAlign: "center", gap: 15, padding: "30px 8px" }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 60,
                      height: 60,
                      borderRadius: "50%",
                      background: "#DDEEE0"
                    }}
                  >
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="#2E7A4E" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </span>
                  <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 25, fontWeight: 600 }}>Request received</h3>
                  <p style={{ margin: 0, color: "#6E6757", fontSize: 15, lineHeight: 1.55, maxWidth: 300 }}>
                    Thanks{thanksName} — we&apos;ll reach out within one business day with next steps
                    for your sample audit.
                  </p>
                  <button
                    onClick={() => {
                      setSubmitted(false);
                      setForm(emptyForm);
                    }}
                    style={{
                      height: 44,
                      padding: "0 20px",
                      border: "1px solid #C9C1AF",
                      borderRadius: 8,
                      background: "#fff",
                      color: "#1A1813",
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: "pointer",
                      fontFamily: SANS
                    }}
                  >
                    Submit another
                  </button>
                </div>
              )
            ) : (
              <div style={{ display: "grid", placeItems: "center", textAlign: "center", gap: 16, padding: "40px 8px" }}>
                <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 24, fontWeight: 600 }}>Ready when you are.</h3>
                <p style={{ margin: 0, color: "#6E6757", fontSize: 15, lineHeight: 1.55, maxWidth: 300 }}>
                  Reach out and we&apos;ll set up your 5-record sample audit.
                </p>
                <a
                  href="mailto:hello@getbellwether.com"
                  style={{
                    height: 48,
                    display: "inline-flex",
                    alignItems: "center",
                    padding: "0 24px",
                    borderRadius: 8,
                    background: "#1A1813",
                    color: "#F2EEE5",
                    fontSize: 15,
                    fontWeight: 600,
                    textDecoration: "none"
                  }}
                >
                  Contact the team
                </a>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ maxWidth: 1200, margin: "0 auto", padding: "48px 28px 44px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1.5fr) repeat(3,minmax(0,1fr))",
            gap: 32
          }}
        >
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 11 }}>
              <Logo size={34} />
              <strong style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Bellwether</strong>
            </div>
            <p style={{ margin: "14px 0 0", maxWidth: 300, color: "#6E6757", fontSize: 13.5, lineHeight: 1.6 }}>
              An AI-native FSMA 204 readiness and remediation system for food traceability.
            </p>
          </div>
          <div style={{ display: "grid", gap: 11, alignContent: "start" }}>
            <strong style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>
              Product
            </strong>
            <a href="#check" style={{ color: "#454035", fontSize: 14, textDecoration: "none" }}>What we check</a>
            <a href="#report" style={{ color: "#454035", fontSize: 14, textDecoration: "none" }}>Sample report</a>
            <a href="#how" style={{ color: "#454035", fontSize: 14, textDecoration: "none" }}>How it works</a>
          </div>
          <div style={{ display: "grid", gap: 11, alignContent: "start" }}>
            <strong style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>
              Sequence
            </strong>
            <span style={{ color: "#454035", fontSize: 14 }}>Bellwether Audit</span>
            <span style={{ color: "#454035", fontSize: 14 }}>Bellwether Remediation</span>
            <span style={{ color: "#454035", fontSize: 14 }}>Bellwether Integrations</span>
          </div>
          <div style={{ display: "grid", gap: 11, alignContent: "start" }}>
            <strong style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>
              Get started
            </strong>
            <a href="#request" style={{ color: "#454035", fontSize: 14, textDecoration: "none" }}>Request a sample audit</a>
            <a href="mailto:hello@getbellwether.com" style={{ color: "#454035", fontSize: 14, textDecoration: "none" }}>
              hello@getbellwether.com
            </a>
            <span style={{ color: "#454035", fontSize: 14 }}>getbellwether.com</span>
          </div>
        </div>
        <div
          style={{
            marginTop: 32,
            paddingTop: 20,
            borderTop: "1px solid #DDD6C7",
            display: "flex",
            flexWrap: "wrap",
            gap: 14,
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <span style={{ fontFamily: MONO, color: "#9A9181", fontSize: 11, letterSpacing: ".03em" }}>© 2026 BELLWETHER</span>
          <span style={{ maxWidth: 680, color: "#9A9181", fontSize: 11.5, lineHeight: 1.5 }}>
            Bellwether Audit is a preliminary readiness review and is not a legal opinion,
            certification, or substitute for professional regulatory advice.
          </span>
        </div>
      </footer>
    </div>
  );
}
