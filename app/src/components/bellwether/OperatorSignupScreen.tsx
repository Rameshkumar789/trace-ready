import type { CSSProperties } from "react";
import Link from "next/link";
import { signUpAction } from "@/app/login/[role]/actions";
import { BellwetherFonts, BellwetherMark, MONO, SANS, SERIF } from "./brand";

// Frame 2 of the design — operator signup. The form still calls the live
// signUpAction server action with the same field names. The action validates a
// confirm-password match and a 12-char minimum, so a "Confirm password" field is
// kept (the design omitted it); the design's "Operation type" select is included
// as operationType (the action ignores it, so it's harmless presentation).

const fieldLabel: CSSProperties = {
  display: "grid",
  gap: 8,
  fontFamily: MONO,
  fontSize: 10,
  letterSpacing: ".05em",
  color: "#6E6757",
  textTransform: "uppercase"
};

const fieldInput: CSSProperties = {
  height: 44,
  border: "1px solid #D7CFBE",
  borderRadius: 8,
  padding: "0 12px",
  fontSize: 14,
  fontFamily: SANS,
  color: "#1A1813",
  background: "#fff"
};

const steps = [
  ["1", "Upload sample records", "Invoices, BOLs, ASNs, labels, or ERP/WMS exports."],
  ["2", "Run a readiness audit", "Scope, KDEs, lot-code lineage, transformation, sharing."],
  ["3", "Export your gap report", "R/Y/G verdict, scorecard, remediation checklist."]
];

export function OperatorSignupScreen({ error, loginHref }: { error?: string; loginHref: string }) {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#FBFAF5",
        fontFamily: SANS,
        color: "#1A1813",
        display: "grid",
        gridTemplateColumns: "minmax(0,1fr) minmax(0,1.05fr)"
      }}
    >
      <BellwetherFonts />
        {/* LEFT — form */}
        <div style={{ padding: "46px 56px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 12, marginBottom: 30 }}>
            <BellwetherMark size={36} />
            <strong style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 600 }}>Bellwether</strong>
          </div>
          <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Create operator account</span>
          <h3 style={{ margin: "10px 0 0", fontFamily: SERIF, fontSize: 28, fontWeight: 600 }}>Get traceability-ready.</h3>
          <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 14.5 }}>
            Already have access?{" "}
            <Link href={loginHref} style={{ color: "#1E3A2C", fontWeight: 600, textDecoration: "none", borderBottom: "1px solid #C9C1AF" }}>
              Sign in
            </Link>
          </p>

          {error ? (
            <p style={{ margin: "16px 0 0", padding: "10px 13px", borderRadius: 8, border: "1px solid #E7C9C0", background: "#F6E3DE", color: "#8F2D22", fontSize: 13.5, lineHeight: 1.5 }}>
              {error}
            </p>
          ) : null}

          <form action={signUpAction} style={{ display: "grid", gap: 15, marginTop: 26 }}>
            <input name="loginRole" type="hidden" value="operator" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 13 }}>
              <label style={fieldLabel}>
                Full name
                <input autoComplete="name" name="fullName" type="text" required placeholder="Dana Ruiz" style={fieldInput} />
              </label>
              <label style={fieldLabel}>
                Company
                <input autoComplete="organization" name="companyName" type="text" required placeholder="Riverbend Produce" style={fieldInput} />
              </label>
            </div>
            <label style={fieldLabel}>
              Work email
              <input autoComplete="email" name="email" type="email" required placeholder="dana@company.com" style={fieldInput} />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 13 }}>
              <label style={fieldLabel}>
                Password
                <input autoComplete="new-password" name="password" type="password" minLength={12} required placeholder="At least 12 characters" style={fieldInput} />
              </label>
              <label style={fieldLabel}>
                Confirm password
                <input autoComplete="new-password" name="confirmPassword" type="password" minLength={12} required placeholder="Re-enter password" style={fieldInput} />
              </label>
            </div>
            <label style={fieldLabel}>
              Operation type
              <select name="operationType" defaultValue="Distributor" style={{ ...fieldInput, padding: "0 10px" }}>
                <option>Distributor</option>
                <option>Packer / repacker</option>
                <option>Food hub</option>
              </select>
            </label>
            <button type="submit" style={{ height: 50, border: "none", borderRadius: 8, background: "#1A1813", color: "#F2EEE5", fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: SANS, marginTop: 4 }}>
              Create account
            </button>
            <small style={{ fontFamily: MONO, color: "#9A9181", fontSize: 10, lineHeight: 1.5, letterSpacing: ".02em" }}>
              YOU&apos;LL CONFIRM YOUR EMAIL BEFORE FIRST SIGN-IN.
            </small>
          </form>
        </div>

        {/* RIGHT — what happens next */}
        <div style={{ background: "#1E3A2C", color: "#EBE6D8", padding: "48px 46px", display: "flex", flexDirection: "column", minHeight: 600 }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9DB39A", textTransform: "uppercase" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#37C07D" }} />
            What happens next
          </span>
          <h2 style={{ margin: "16px 0 0", fontFamily: SERIF, fontSize: 32, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-.015em" }}>
            From sign-up to readiness report.
          </h2>
          <div style={{ marginTop: 30, display: "grid", gap: 0, borderTop: "1px solid rgba(255,255,255,.16)" }}>
            {steps.map(([n, title, copy], i) => (
              <div
                key={n}
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr",
                  gap: 16,
                  padding: "18px 0",
                  borderBottom: i < steps.length - 1 ? "1px solid rgba(255,255,255,.16)" : undefined
                }}
              >
                <span style={{ fontFamily: SERIF, fontSize: 22, color: "#7FC79D" }}>{n}</span>
                <div>
                  <strong style={{ display: "block", fontSize: 15 }}>{title}</strong>
                  <span style={{ color: "#9DB39A", fontSize: 13, lineHeight: 1.5 }}>{copy}</span>
                </div>
              </div>
            ))}
          </div>
          <p style={{ marginTop: "auto", paddingTop: 30, fontFamily: MONO, fontSize: 10, color: "#7E9583", lineHeight: 1.6, letterSpacing: ".02em" }}>
            REDACTED SAMPLES ONLY · WE NEVER ASK FOR PRODUCTION CREDENTIALS.
          </p>
        </div>
    </main>
  );
}
