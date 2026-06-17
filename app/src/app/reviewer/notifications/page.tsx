import Link from "next/link";
import { AppShell } from "@/components/AppShell";

export default function ReviewerNotificationsPage() {
  return (
    <AppShell>
      <section className="utility-page">
        <div className="utility-header">
          <span className="eyebrow">Notifications</span>
          <h1>No reviewer notifications.</h1>
          <p>Pending rule cards, failed coverage gates, source-version changes, and scenario regressions will appear here.</p>
        </div>
        <article className="utility-card">
          <h2>Notification plan</h2>
          <p>Next implementation: create Supabase notification events from ingestion runs, approval actions, and regression locks.</p>
        </article>
        <Link className="button secondary" href="/reviewer">Back to Reviewer Home</Link>
      </section>
    </AppShell>
  );
}
