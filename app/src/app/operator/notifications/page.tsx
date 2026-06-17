import Link from "next/link";
import { AppShell } from "@/components/AppShell";

export default function OperatorNotificationsPage() {
  return (
    <AppShell>
      <section className="utility-page">
        <div className="utility-header">
          <span className="eyebrow">Notifications</span>
          <h1>No new notifications.</h1>
          <p>Audit status, reviewer comments, export readiness, and failed upload alerts will appear here.</p>
        </div>
        <article className="utility-card">
          <h2>Notification plan</h2>
          <p>Next implementation: store notification records in Supabase, mark them read/unread, and link each item to the audit or finding that needs action.</p>
        </article>
        <Link className="button secondary" href="/operator">Back to Home</Link>
      </section>
    </AppShell>
  );
}
