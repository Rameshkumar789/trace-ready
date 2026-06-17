import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { arrayLength, blockersForDraft, loadDraftRecord, type DraftRecordRow } from "@/lib/regulatory/regulatory-admin-db";
import { approveRegulatoryDraftAction, rejectRegulatoryDraftAction } from "../actions";

export default async function RegulatoryDraftReviewDetailPage({ params }: { params: Promise<{ draftId: string }> }) {
  const session = await getTraceReadySession();
  const { draftId } = await params;
  const nextPath = `/admin/regulatory/review/${encodeURIComponent(draftId)}`;
  if (!session || !canAccessPath(session, nextPath)) {
    redirect(`/login/reviewer?auth=required&next=${nextPath}`);
  }
  const draft = await loadDraftRecord(draftId);
  if (!draft) notFound();
  const blockers = blockersForDraft(draft);
  const ready = draft.review_status === "needs_review" && draft.schema_valid && draft.citation_valid && blockers.length === 0;

  return (
    <AppShell>
      <div className="reg-review-page">
        <section className="reg-review-header">
          <div>
            <span className="eyebrow">Review Queue</span>
            <h1>{formatDraftName(draft)}</h1>
            <p>{draft.record_id}</p>
          </div>
          <Link className="button secondary" href="/admin/regulatory/review">Back to queue</Link>
        </section>

        <section className="reg-review-detail-grid">
          <article className="reg-review-detail-card">
            <h2>Draft Summary</h2>
            <dl className="reg-review-detail-list">
              <div><dt>Collection</dt><dd>{humanize(draft.collection)}</dd></div>
              <div><dt>Method</dt><dd>{humanize(draft.extraction_method)}</dd></div>
              <div><dt>Source phase</dt><dd>{humanize(draft.source_phase)}</dd></div>
              <div><dt>Status</dt><dd><ReviewStatusBadge draft={draft} ready={ready} /></dd></div>
              <div><dt>Evidence</dt><dd>{arrayLength(draft.source_chunk_ids)} chunks · {draft.citation_count} citations</dd></div>
              <div><dt>Citation coverage</dt><dd>{draft.citation_coverage_status}</dd></div>
            </dl>
          </article>

          <article className="reg-review-detail-card">
            <h2>Review Decision</h2>
            {blockers.length ? (
              <div className="reg-review-blocker-box">
                <strong>Blockers</strong>
                <ul>
                  {blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
                </ul>
              </div>
            ) : (
              <p className="muted">No schema, citation, or reviewer blockers were recorded.</p>
            )}
            <div className="reg-review-detail-actions">
              <form action={approveRegulatoryDraftAction}>
                <input name="draftId" type="hidden" value={draft.id} />
                <input name="next" type="hidden" value="/admin/regulatory/review" />
                <label>
                  Approval note
                  <textarea disabled={!ready} name="reason" placeholder="Why is this draft supported by the cited source?" required />
                </label>
                <button disabled={!ready} type="submit">Approve draft</button>
              </form>
              <form action={rejectRegulatoryDraftAction}>
                <input name="draftId" type="hidden" value={draft.id} />
                <input name="next" type="hidden" value="/admin/regulatory/review" />
                <label>
                  Rejection reason
                  <textarea name="reason" placeholder="What needs correction before approval?" required />
                </label>
                <button className="danger" type="submit">Reject draft</button>
              </form>
            </div>
          </article>
        </section>

        <section className="reg-review-detail-card">
          <h2>Payload</h2>
          <pre className="reg-review-payload">{JSON.stringify(draft.payload ?? {}, null, 2)}</pre>
        </section>
      </div>
    </AppShell>
  );
}

function ReviewStatusBadge({ draft, ready }: { draft: DraftRecordRow; ready: boolean }) {
  if (ready) return <span className="review-status ready">Ready</span>;
  if (!draft.schema_valid) return <span className="review-status blocked">Schema issue</span>;
  if (!draft.citation_valid) return <span className="review-status blocked">Citation issue</span>;
  return <span className="review-status">Needs review</span>;
}

function formatDraftName(draft: DraftRecordRow) {
  const payload = asRecord(draft.payload);
  return (
    stringFrom(payload.title) ??
    stringFrom(payload.ruleTitle) ??
    stringFrom(payload.kdeName) ??
    stringFrom(payload.name) ??
    stringFrom(payload.decisionQuestion) ??
    humanize(draft.record_id.replace(/^(scenario[_-])+/i, ""))
  );
}

function humanize(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function stringFrom(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
