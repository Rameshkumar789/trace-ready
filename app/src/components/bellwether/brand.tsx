import type { CSSProperties } from "react";

// Shared Bellwether design primitives, ported from the Claude Design project
// "Bellwether main page" (file: Bellwether App Screens.dc.html). Fonts, the logo
// mark, and the type stacks are reused across the login, signup, operator
// dashboard, and audits screens so each page stays a faithful inline-style port.

export const MONO = "'JetBrains Mono',monospace";
export const SERIF = "'Newsreader',serif";
export const SANS = "'Hanken Grotesk',ui-sans-serif,system-ui,sans-serif";

/** Google Fonts + base smoothing/selection, ported from the design's <helmet>.
 *  Render once per page; React 19 hoists <link>/<style> into <head>. */
export function BellwetherFonts() {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <style>{`
        body { margin:0; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }
        ::selection { background:#1E3A2C; color:#F2EEE5; }
      `}</style>
    </>
  );
}

/** The Bellwether badge logo. `inner` is the rounded-rect fill — the design uses
 *  #1E3A2C on light surfaces and the darker #16291F inside the green panels. */
export function BellwetherMark({
  size = 34,
  inner = "#1E3A2C",
  rx = 11
}: {
  size?: number;
  inner?: string;
  rx?: number;
}) {
  return (
    <svg viewBox="0 0 44 44" style={{ width: size, height: size, display: "block" }}>
      <rect x="1" y="1" width="42" height="42" rx={rx} fill={inner} />
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
}

/** Mono "chip" pill used for statuses across the screens. */
export function monoPill(color: string, bg: string, pad = "3px 9px"): CSSProperties {
  return {
    fontFamily: MONO,
    fontSize: 11,
    color,
    background: bg,
    padding: pad,
    borderRadius: 6,
    width: "fit-content"
  };
}
