import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { getBellwetherSession } from "@/lib/auth/session";
import { BellwetherFonts, BellwetherMark, MONO, SANS, SERIF } from "./brand";

// Bellwether operator app shell — dark-green sidebar + cream workspace, ported
// from frames 3 & 4 of the design. Reads the real Bellwether session for the
// profile chip; nav links point at the live routes (Reports/Settings have no
// route yet, so they render as inert items, matching the design's 5-item rail).

type NavKey = "dashboard" | "audits" | "upload" | "reports" | "settings";

const ICONS: Record<NavKey, ReactNode> = {
  dashboard: (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" />
      <rect x="14" y="3" width="7" height="5" />
      <rect x="14" y="12" width="7" height="9" />
      <rect x="3" y="16" width="7" height="5" />
    </svg>
  ),
  audits: (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M9 13h6M9 17h6" />
    </svg>
  ),
  upload: (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5-5 5 5M12 5v12" />
    </svg>
  ),
  reports: (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 3 3 5-6" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15H4.5a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 6 9.4l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 11 4.6h.09A2 2 0 0 1 15 4.5v.09c.7.16 1.36.52 1.82 1.06" />
    </svg>
  )
};

const NAV: Array<{ key: NavKey; label: string; href: string }> = [
  { key: "dashboard", label: "Dashboard", href: "/operator" },
  { key: "audits", label: "Audits", href: "/operator/audits" },
  { key: "upload", label: "Upload records", href: "/operator/upload" },
  { key: "reports", label: "Reports", href: "/operator/reports" },
  { key: "settings", label: "Settings", href: "/operator/settings" }
];

function initials(name?: string, email?: string): string {
  const source = name?.trim() || email?.split("@")[0] || "";
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "BW";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export async function BellwetherShell({
  active,
  topbarLeft,
  topbarRight,
  children
}: {
  active?: NavKey;
  topbarLeft: ReactNode;
  topbarRight?: ReactNode;
  children: ReactNode;
}) {
  const session = await getBellwetherSession();
  const name = session?.fullName ?? session?.email ?? "Operator";
  const company = session?.companyName ?? "Riverbend Produce";

  const navItemBase: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 11,
    padding: "10px 12px",
    borderRadius: 8,
    fontSize: 14,
    textDecoration: "none"
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "240px 1fr",
        minHeight: "100vh",
        background: "#EFEADF",
        color: "#1A1813",
        fontFamily: SANS
      }}
    >
      <BellwetherFonts />

      {/* SIDEBAR */}
      <aside style={{ background: "#1E3A2C", color: "#C6CEBC", padding: "22px 16px", display: "flex", flexDirection: "column" }}>
        <Link href="/operator" style={{ display: "inline-flex", alignItems: "center", gap: 11, padding: "6px 8px", textDecoration: "none" }}>
          <BellwetherMark size={34} inner="#16291F" rx={10} />
          <strong style={{ fontFamily: SERIF, fontSize: 19, fontWeight: 600, color: "#F2EEE5" }}>Bellwether</strong>
        </Link>
        <nav style={{ marginTop: 26, display: "grid", gap: 3 }}>
          {NAV.map((item) => {
            const isActive = item.key === active;
            return (
              <Link
                key={item.key}
                href={item.href}
                style={{
                  ...navItemBase,
                  background: isActive ? "#2C4636" : "transparent",
                  color: isActive ? "#F2EEE5" : "#A8B5A0",
                  fontWeight: isActive ? 600 : 500
                }}
              >
                {ICONS[item.key]}
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div style={{ marginTop: "auto", borderTop: "1px solid rgba(255,255,255,.12)", paddingTop: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 11, padding: 8 }}>
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 9,
                background: "#7FC79D",
                color: "#16291F",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 13,
                flex: "none"
              }}
            >
              {initials(session?.fullName, session?.email)}
            </span>
            <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.2, overflow: "hidden" }}>
              <strong style={{ fontSize: 13, color: "#F2EEE5", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{name}</strong>
              <small style={{ fontSize: 11, color: "#9DB39A", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Operator · {company}</small>
            </span>
          </div>
          <form action="/logout" method="post">
            <button
              type="submit"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 11,
                width: "100%",
                padding: "9px 12px",
                marginTop: 2,
                borderRadius: 8,
                border: "none",
                background: "transparent",
                color: "#CDA199",
                fontSize: 13.5,
                fontWeight: 500,
                fontFamily: "inherit",
                cursor: "pointer",
                textAlign: "left"
              }}
            >
              <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="M16 17l5-5-5-5" />
                <path d="M21 12H9" />
              </svg>
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* MAIN */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div
          style={{
            height: 60,
            borderBottom: "1px solid #DDD6C7",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 28px",
            background: "#FBFAF5"
          }}
        >
          <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".06em", color: "#9A9181" }}>{topbarLeft}</span>
          {topbarRight ? <div style={{ display: "flex", alignItems: "center", gap: 14 }}>{topbarRight}</div> : null}
        </div>
        {children}
      </div>
    </div>
  );
}
