import type { CSSProperties } from "react";
import Link from "next/link";
import { BellwetherFonts, BellwetherMark, MONO, SANS, SERIF } from "./brand";

// Frame 1 of the design — operator login. The form still posts to the live
// /auth/login route handler with the same hidden loginRole/next fields, so all
// auth wiring is preserved; only the presentation is the Bellwether port.

const fieldLabel: CSSProperties = {
  display: "grid",
  gap: 8,
  fontFamily: MONO,
  fontSize: 10.5,
  letterSpacing: ".05em",
  color: "#6E6757",
  textTransform: "uppercase"
};

const fieldInput: CSSProperties = {
  height: 46,
  border: "1px solid #D7CFBE",
  borderRadius: 8,
  padding: "0 13px",
  fontSize: 14.5,
  fontFamily: SANS,
  color: "#1A1813",
  background: "#fff"
};

const valueProps = [
  "Red / yellow / green readiness verdict",
  "Supplier scorecard & remediation checklist",
  "FDA-style export package with citations"
];

export function OperatorLoginScreen({
  next,
  error,
  authRequired,
  confirmEmail,
  confirmEmailAddress,
  signupHref
}: {
  next: string;
  error?: string;
  authRequired?: boolean;
  confirmEmail?: boolean;
  confirmEmailAddress?: string;
  signupHref: string;
}) {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#FBFAF5",
        fontFamily: SANS,
        color: "#1A1813",
        display: "grid",
        gridTemplateColumns: "minmax(0,1.05fr) minmax(0,1fr)"
      }}
    >
      <BellwetherFonts />
        {/* LEFT — value props */}
        <div
          style={{
            background: "#1E3A2C",
            color: "#EBE6D8",
            padding: "48px 46px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 30,
            minHeight: 560
          }}
        >
          <div style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
            <BellwetherMark size={40} inner="#16291F" />
            <span style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
              <strong style={{ fontFamily: SERIF, fontSize: 21, fontWeight: 600 }}>Bellwether</strong>
              <small style={{ marginTop: 4, fontFamily: MONO, color: "#9DB39A", fontSize: 9.5, letterSpacing: ".08em" }}>AUDIT · REMEDIATION</small>
            </span>
          </div>
          <div>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9DB39A", textTransform: "uppercase" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#37C07D" }} />
              Workbook audit access
            </span>
            <h2 style={{ margin: "16px 0 0", fontFamily: SERIF, fontSize: 38, lineHeight: 1.08, fontWeight: 500, letterSpacing: "-.015em" }}>
              Enter the operator workspace.
            </h2>
            <p style={{ margin: "16px 0 0", maxWidth: 380, color: "#C6CEBC", fontSize: 15.5, lineHeight: 1.6 }}>
              Upload traceability workbooks, run readiness audits, resolve gaps, and export evidence
              packages — every finding linked to a record and a rule.
            </p>
          </div>
          <div style={{ display: "grid", gap: 11 }}>
            {valueProps.map((v) => (
              <div key={v} style={{ display: "flex", alignItems: "center", gap: 11, fontSize: 14, color: "#D8DECF" }}>
                <span style={{ fontFamily: MONO, color: "#5FB98E" }}>✓</span>
                {v}
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT — sign-in form */}
        <div style={{ padding: "48px 56px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Sign in</span>
          <h3 style={{ margin: "10px 0 0", fontFamily: SERIF, fontSize: 28, fontWeight: 600 }}>Welcome back.</h3>
          <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 14.5 }}>
            New operator?{" "}
            <Link href={signupHref} style={{ color: "#1E3A2C", fontWeight: 600, textDecoration: "none", borderBottom: "1px solid #C9C1AF" }}>
              Create an account
            </Link>
          </p>

          {authRequired ? (
            <p style={{ ...notice("#8A5E0E", "#F7ECCE", "#EAD9A8") }}>Sign in to continue.</p>
          ) : null}
          {confirmEmail ? (
            <p style={{ ...notice("#1F5638", "#DDEEE0", "#C2E0CB") }}>
              Account created. Confirm {confirmEmailAddress ?? "your email"}, then sign in with your password.
            </p>
          ) : null}
          {error ? <p style={{ ...notice("#8F2D22", "#F6E3DE", "#E7C9C0") }}>{error}</p> : null}

          <form action="/auth/login" method="post" style={{ display: "grid", gap: 16, marginTop: 30 }}>
            <input name="loginRole" type="hidden" value="operator" />
            <input name="next" type="hidden" value={next} />
            <label style={fieldLabel}>
              Work email
              <input autoComplete="email" name="email" type="email" required placeholder="name@company.com" style={fieldInput} />
            </label>
            <label style={fieldLabel}>
              Password
              <input autoComplete="current-password" name="password" type="password" required placeholder="Enter your password" style={fieldInput} />
            </label>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13.5, color: "#454035" }}>
                <input name="remember" type="checkbox" defaultChecked style={{ width: 16, height: 16, accentColor: "#1E3A2C" }} />
                Stay signed in
              </label>
              <Link href="/login/operator" style={{ fontSize: 13.5, color: "#6E6757", textDecoration: "none" }}>Forgot password?</Link>
            </div>
            <button type="submit" style={{ height: 50, border: "none", borderRadius: 8, background: "#1A1813", color: "#F2EEE5", fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: SANS }}>
              Sign in to workspace
            </button>
          </form>

          <div style={{ marginTop: 26, paddingTop: 18, borderTop: "1px solid #E4DDCD", display: "flex", gap: 20 }}>
            <Link href="/" style={{ fontSize: 13, color: "#6E6757", textDecoration: "none" }}>Back to overview</Link>
          </div>
        </div>
    </main>
  );
}

function notice(color: string, bg: string, border: string): CSSProperties {
  return {
    margin: "18px 0 0",
    padding: "10px 13px",
    borderRadius: 8,
    border: `1px solid ${border}`,
    background: bg,
    color,
    fontSize: 13.5,
    lineHeight: 1.5
  };
}
