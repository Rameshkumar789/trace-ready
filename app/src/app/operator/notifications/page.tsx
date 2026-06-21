import Link from "next/link";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF } from "@/components/bellwether/brand";

export default function OperatorNotificationsPage() {
  return (
    <BellwetherShell topbarLeft="NOTIFICATIONS">
      <div style={{ padding: "28px", maxWidth: 900 }}>
        <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".08em", color: "#9A9181", textTransform: "uppercase" }}>Notifications</span>
        <h1 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 30, fontWeight: 500, letterSpacing: "-.015em" }}>No new notifications.</h1>
        <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 14.5, lineHeight: 1.6, maxWidth: 560 }}>
          Audit status, reviewer comments, export readiness, and failed upload alerts will appear here.
        </p>
        <article style={{ background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12, padding: 20, marginTop: 22, maxWidth: 560 }}>
          <h2 style={{ margin: 0, fontFamily: SERIF, fontSize: 17, fontWeight: 600 }}>Notification plan</h2>
          <p style={{ margin: "8px 0 0", color: "#6E6757", fontSize: 13.5, lineHeight: 1.55 }}>
            Next implementation: store notification records in Supabase, mark them read/unread, and link each item to the audit or finding that needs action.
          </p>
        </article>
        <Link
          href="/operator"
          style={{ display: "inline-flex", alignItems: "center", height: 48, padding: "0 22px", marginTop: 24, borderRadius: 8, background: "transparent", color: "#1A1813", border: "1px solid #C9C1AF", fontSize: 15, fontWeight: 600, textDecoration: "none" }}
        >
          Back to Home
        </Link>
      </div>
    </BellwetherShell>
  );
}
