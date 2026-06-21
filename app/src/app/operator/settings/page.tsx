import { redirect } from "next/navigation";
import type { CSSProperties } from "react";
import { getBellwetherSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/roles";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF, monoPill } from "@/components/bellwether/brand";
import { changePasswordAction, saveSettingsAction } from "./actions";

// Frame 7 — workspace settings, fully wired. Org/account/notification fields save
// to bellwether_profiles + Supabase user_metadata via saveSettingsAction; change
// password sends a Supabase reset email. The team roster is still representative
// (no memberships query surfaced yet).

const card = { background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12 } as const;
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
  fontFamily: "'Hanken Grotesk',sans-serif",
  color: "#1A1813",
  background: "#fff"
};

function Switch({ name, defaultOn }: { name: string; defaultOn: boolean }) {
  return (
    <label className="bw-switch">
      <input type="checkbox" name={name} defaultChecked={defaultOn} />
      <span className="track">
        <span className="thumb" />
      </span>
    </label>
  );
}

const team = [
  { initials: "DR", name: "Dana Ruiz", email: "dana@riverbendproduce.com", role: "Owner", roleColor: "#1F5638", roleBg: "#DDEEE0", avatarBg: "#7FC79D", avatarColor: "#16291F" },
  { initials: "MK", name: "Marcus Kim", email: "marcus@riverbendproduce.com", role: "Editor", roleColor: "#454035", roleBg: "#EFE9DC", avatarBg: "#C9D6CB", avatarColor: "#1E3A2C" },
  { initials: "JW", name: "Jim White", email: "jim@bellwether.audit", role: "Reviewer", roleColor: "#454035", roleBg: "#EFE9DC", avatarBg: "#C9D6CB", avatarColor: "#1E3A2C" }
];

function metaStr(meta: Record<string, unknown> | undefined, key: string, fallback = ""): string {
  const v = meta?.[key];
  return typeof v === "string" ? v : fallback;
}
function metaBool(meta: Record<string, unknown> | undefined, key: string, fallback: boolean): boolean {
  const v = meta?.[key];
  return typeof v === "boolean" ? v : fallback;
}

export default async function SettingsPage({ searchParams }: { searchParams?: Promise<{ saved?: string; reset?: string }> }) {
  const session = await getBellwetherSession();
  if (!session || !canAccessPath(session, "/operator/settings")) {
    redirect("/login/operator?auth=required&next=/operator/settings");
  }
  const sp = await searchParams;
  const supabase = await createServerSupabaseClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();
  const meta = user?.user_metadata as Record<string, unknown> | undefined;

  return (
    <BellwetherShell
      active="settings"
      topbarLeft="SETTINGS"
      topbarRight={
        <button type="submit" form="settings-form" style={{ height: 38, padding: "0 16px", border: "none", borderRadius: 8, background: "#1E3A2C", color: "#F2EEE5", fontSize: 13.5, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
          Save changes
        </button>
      }
    >
      <style>{`
        .bw-switch { position: relative; display: inline-block; width: 42px; height: 24px; flex: none; cursor: pointer; }
        .bw-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
        .bw-switch .track { position: absolute; inset: 0; border-radius: 99px; background: #C9C1AF; transition: background .15s; }
        .bw-switch .thumb { position: absolute; top: 2px; left: 2px; width: 20px; height: 20px; border-radius: 50%; background: #fff; transition: left .15s; }
        .bw-switch input:checked + .track { background: #1E3A2C; }
        .bw-switch input:checked + .track .thumb { left: 20px; }
      `}</style>

      <div style={{ padding: 28 }}>
        <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Settings</span>
        <h2 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>Workspace settings</h2>
        <p style={{ margin: "6px 0 0", color: "#6E6757", fontSize: 14 }}>Manage your organization profile, account, notifications, and team.</p>

        {sp?.saved ? <Banner ok>Settings saved.</Banner> : null}
        {sp?.reset === "sent" ? <Banner ok>Password reset email sent to {session.email}.</Banner> : null}
        {sp?.reset === "error" ? <Banner>Could not send the reset email — try again.</Banner> : null}

        <form id="settings-form" action={saveSettingsAction}>
          {/* Organization */}
          <div style={{ ...card, padding: 24, marginTop: 20 }}>
            <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Organization profile</h3>
            <p style={{ margin: "5px 0 0", color: "#6E6757", fontSize: 13 }}>Used to scope your products against the Food Traceability List.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 15, marginTop: 18 }}>
              <label style={fieldLabel}>Company name<input name="companyName" defaultValue={session.companyName ?? ""} style={fieldInput} /></label>
              <label style={fieldLabel}>
                Operation type
                <select name="operationType" defaultValue={metaStr(meta, "operation_type", "Distributor")} style={{ ...fieldInput, padding: "0 10px" }}>
                  <option>Distributor</option>
                  <option>Packer / repacker</option>
                  <option>Food hub</option>
                </select>
              </label>
              <label style={fieldLabel}>Facilities<input name="facilities" defaultValue={metaStr(meta, "facilities")} style={fieldInput} /></label>
              <label style={fieldLabel}>Primary commodity<input name="primaryCommodity" defaultValue={metaStr(meta, "primary_commodity")} style={fieldInput} /></label>
            </div>
          </div>

          {/* Account + Notifications */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 14 }}>
            <div style={{ ...card, padding: 24 }}>
              <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Account &amp; security</h3>
              <div style={{ display: "grid", gap: 15, marginTop: 18 }}>
                <label style={fieldLabel}>Full name<input name="fullName" defaultValue={session.fullName ?? ""} style={fieldInput} /></label>
                <label style={fieldLabel}>Work email<input defaultValue={session.email} disabled style={{ ...fieldInput, background: "#F4F0E6", color: "#6E6757" }} /></label>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 4 }}>
                  <div>
                    <strong style={{ display: "block", fontSize: 13.5 }}>Two-factor authentication</strong>
                    <span style={{ fontSize: 12, color: "#6E6757" }}>Required for evidence exports</span>
                  </div>
                  <Switch name="two_factor" defaultOn={metaBool(meta, "two_factor", true)} />
                </div>
              </div>
            </div>
            <div style={{ ...card, padding: 24 }}>
              <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Notifications</h3>
              <div style={{ marginTop: 12 }}>
                {[
                  { key: "notif_audit_complete", title: "Audit complete", detail: "When a readiness audit finishes", def: true },
                  { key: "notif_high_severity", title: "New high-severity finding", detail: "Blockers like a missing TLC-source", def: true },
                  { key: "notif_weekly_summary", title: "Weekly readiness summary", detail: "Monday digest of open gaps", def: false }
                ].map((n, i, arr) => (
                  <div key={n.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "13px 0", borderBottom: i < arr.length - 1 ? "1px solid #EDE7D8" : undefined }}>
                    <div>
                      <strong style={{ display: "block", fontSize: 13.5 }}>{n.title}</strong>
                      <span style={{ fontSize: 12, color: "#6E6757" }}>{n.detail}</span>
                    </div>
                    <Switch name={n.key} defaultOn={metaBool(meta, n.key, n.def)} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </form>

        {/* change password — separate action */}
        <form action={changePasswordAction} style={{ marginTop: 12 }}>
          <button type="submit" style={{ fontSize: 13, color: "#1E3A2C", fontWeight: 600, background: "none", border: "none", borderBottom: "1px solid #C9C1AF", cursor: "pointer", padding: 0, fontFamily: "inherit" }}>
            Change password
          </button>
        </form>

        {/* Team (representative) */}
        <div style={{ ...card, marginTop: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 24px 14px" }}>
            <div>
              <h3 style={{ margin: 0, fontFamily: SERIF, fontSize: 19, fontWeight: 600 }}>Team members</h3>
              <p style={{ margin: "4px 0 0", color: "#6E6757", fontSize: 13 }}>Who can upload records and view reports.</p>
            </div>
            <button style={{ height: 38, padding: "0 15px", border: "1px solid #C9C1AF", borderRadius: 8, background: "#fff", color: "#1A1813", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>+ Invite</button>
          </div>
          {team.map((m, i) => (
            <div key={m.email} style={{ display: "grid", gridTemplateColumns: "1.6fr 1.4fr 1fr auto", gap: 14, alignItems: "center", padding: "13px 24px", borderTop: i === 0 ? "1px solid #E4DDCD" : undefined, borderBottom: i < team.length - 1 ? "1px solid #EDE7D8" : undefined }}>
              <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
                <span style={{ width: 32, height: 32, borderRadius: 8, background: m.avatarBg, color: m.avatarColor, display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12 }}>{m.initials}</span>
                <span style={{ fontWeight: 600, fontSize: 13.5 }}>{m.name}</span>
              </div>
              <span style={{ fontSize: 13, color: "#6E6757" }}>{m.email}</span>
              <span style={monoPill(m.roleColor, m.roleBg, "3px 9px")}>{m.role}</span>
              <a href="#" style={{ justifySelf: "end", fontSize: 12.5, color: "#9A9181", textDecoration: "none" }}>Manage</a>
            </div>
          ))}
        </div>

        {/* sign out */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, background: "#FBFAF5", border: "1px solid #E7C9C0", borderRadius: 12, padding: "18px 24px", marginTop: 14 }}>
          <div>
            <strong style={{ display: "block", fontSize: 14 }}>Sign out of Bellwether</strong>
            <span style={{ fontSize: 12.5, color: "#6E6757" }}>End your session on this device.</span>
          </div>
          <form action="/logout" method="post">
            <button
              type="submit"
              style={{ height: 42, padding: "0 18px", border: "1px solid #D8A99E", borderRadius: 8, background: "#fff", color: "#8F2D22", fontSize: 13.5, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", display: "inline-flex", alignItems: "center", gap: 8 }}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="M16 17l5-5-5-5" />
                <path d="M21 12H9" />
              </svg>
              Sign out
            </button>
          </form>
        </div>
      </div>
    </BellwetherShell>
  );
}

function Banner({ ok, children }: { ok?: boolean; children: React.ReactNode }) {
  return (
    <p
      style={{
        margin: "16px 0 0",
        padding: "10px 14px",
        borderRadius: 8,
        border: `1px solid ${ok ? "#C2E0CB" : "#E7C9C0"}`,
        background: ok ? "#E4EFE7" : "#F6E3DE",
        color: ok ? "#1F5638" : "#8F2D22",
        fontSize: 13.5
      }}
    >
      {children}
    </p>
  );
}
