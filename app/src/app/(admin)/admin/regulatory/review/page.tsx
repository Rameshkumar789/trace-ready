import { redirect } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { arrayLength, blockersForDraft, countReadyDraftRecords, listDraftRecordsPage, loadDraftRecord, type DraftRecordRow } from "@/lib/regulatory/regulatory-admin-db";
import { approveRegulatoryDraftAction, rejectRegulatoryDraftAction } from "./actions";

export default async function RegulatoryReviewPage({ searchParams }: { searchParams?: Promise<{ draft?: string; page?: string }> }) {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, "/admin/regulatory/review")) {
    redirect("/login/reviewer?auth=required&next=/admin/regulatory/review");
  }
  const resolvedSearchParams = await searchParams;
  const currentPage = parsePage(resolvedSearchParams?.page);
  const selectedDraftId = stringFrom(resolvedSearchParams?.draft);
  const pageSize = 10;
  const [{ rows: visibleQueue, total: openDraftCount }, readyForReview] = await Promise.all([
    listDraftRecordsPage({ page: currentPage, pageSize, reviewStatus: "needs_review" }),
    countReadyDraftRecords()
  ]);
  const totalPages = Math.max(1, Math.ceil(openDraftCount / pageSize));
  const selectedDraft = selectedDraftId ? await loadDraftRecord(selectedDraftId) : undefined;
  const queuePath = reviewQueueHref(currentPage);

  return (
    <AppShell>
      <div className="reg-review-page">
        <section className="reg-review-header">
          <div>
            <span className="eyebrow">Review Queue</span>
            <h1>Regulatory Review Queue</h1>
            <p>Approve only citation-backed draft rules. Approved drafts become eligible for a published rule package; rejected drafts return to correction.</p>
          </div>
          {selectedDraftId ? (
            <Link className="button secondary reg-review-header-action" href={queuePath}>Back to queue</Link>
          ) : (
            <span className="badge warn">{readyForReview} ready</span>
          )}
        </section>

        {selectedDraftId ? (
          selectedDraft ? (
            <DraftReviewPanel currentPage={currentPage} draft={selectedDraft} />
          ) : (
            <section className="reg-review-detail-card">
              <h2>Draft Not Found</h2>
              <p className="muted">This draft is no longer available in the review queue.</p>
              <Link className="button secondary" href={queuePath}>Back to queue</Link>
            </section>
          )
        ) : (
          <section className="reg-review-table-card">
            <div className="reg-review-table-heading">
              <div>
                <h2>Open draft reviews</h2>
                <p>Showing {visibleQueue.length} of {openDraftCount} draft records awaiting reviewer action. Use View details to inspect, approve, or reject a draft.</p>
              </div>
            </div>

            {visibleQueue.length ? (
              <div className="reg-review-table-wrap">
                <table className="reg-review-table">
                  <thead>
                    <tr>
                      <th>Draft</th>
                      <th>Status</th>
                      <th>Evidence</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleQueue.map((draft) => {
                      const blockers = blockersForDraft(draft);
                      const ready = draft.schema_valid && draft.citation_valid && blockers.length === 0;
                      return (
                        <tr key={draft.id}>
                          <td>
                            <div className="reg-review-draft">
                              <Link href={reviewQueueHref(currentPage, draft.id)}>{formatDraftName(draft)}</Link>
                              <span>{humanize(draft.collection)} · {humanize(draft.extraction_method)}</span>
                            </div>
                          </td>
                          <td><ReviewStatusBadge draft={draft} ready={ready} /></td>
                          <td>
                            <span>{arrayLength(draft.source_chunk_ids)} chunks</span>
                            <small>{draft.citation_count} citations</small>
                          </td>
                          <td>
                            <Link className="reg-review-open-link" href={reviewQueueHref(currentPage, draft.id)}>View details</Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="reviewer-empty-state">
                <h2>No draft records are waiting for review.</h2>
                <p>New draft rules will appear here after source ingestion and validation.</p>
              </div>
            )}
            <div className="reg-review-pagination" aria-label="Review queue pagination">
              <span>Page {currentPage} of {totalPages}</span>
              <div>
                <Link aria-disabled={currentPage <= 1} className={currentPage <= 1 ? "disabled" : ""} href={`/admin/regulatory/review?page=${Math.max(1, currentPage - 1)}`}>Previous</Link>
                <Link aria-disabled={currentPage >= totalPages} className={currentPage >= totalPages ? "disabled" : ""} href={`/admin/regulatory/review?page=${Math.min(totalPages, currentPage + 1)}`}>Next</Link>
              </div>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}

function parsePage(value: string | undefined) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function DraftReviewPanel({ currentPage, draft }: { currentPage: number; draft: DraftRecordRow }) {
  const blockers = blockersForDraft(draft);
  const ready = draft.review_status === "needs_review" && draft.schema_valid && draft.citation_valid && blockers.length === 0;
  const queuePath = reviewQueueHref(currentPage);

  return (
    <section className="reg-review-detail-grid" aria-label="Selected draft review">
      <article className="reg-review-detail-card">
        <div className="reg-review-detail-title-row">
          <div>
            <span className="eyebrow">Selected Draft</span>
            <h2>{formatDraftName(draft)}</h2>
            <p>{draft.record_id}</p>
          </div>
        </div>
        <dl className="reg-review-detail-list">
          <div><dt>Collection</dt><dd>{humanize(draft.collection)}</dd></div>
          <div><dt>Method</dt><dd>{humanize(draft.extraction_method)}</dd></div>
          <div><dt>Source phase</dt><dd>{humanize(draft.source_phase)}</dd></div>
          <div><dt>Status</dt><dd><ReviewStatusBadge draft={draft} ready={ready} /></dd></div>
          <div><dt>Evidence</dt><dd>{arrayLength(draft.source_chunk_ids)} chunks · {draft.citation_count} citations</dd></div>
          <div><dt>Citation coverage</dt><dd>{draft.citation_coverage_status}</dd></div>
        </dl>
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
        <pre className="reg-review-payload">{JSON.stringify(draft.payload ?? {}, null, 2)}</pre>
      </article>

      <article className="reg-review-detail-card">
        <h2>Review Decision</h2>
        <p className="muted">Approve only when the payload is supported by the cited source chunks. Reject when the draft needs correction before it can enter an approved package.</p>
        <div className="reg-review-detail-actions">
          <form action={approveRegulatoryDraftAction}>
            <input name="draftId" type="hidden" value={draft.id} />
            <input name="next" type="hidden" value={queuePath} />
            <label>
              Approval note
              <textarea disabled={!ready} name="reason" placeholder="Why is this draft supported by the cited source?" required />
            </label>
            <button disabled={!ready} type="submit">Approve draft</button>
          </form>
          <form action={rejectRegulatoryDraftAction}>
            <input name="draftId" type="hidden" value={draft.id} />
            <input name="next" type="hidden" value={queuePath} />
            <label>
              Rejection reason
              <textarea name="reason" placeholder="What needs correction before approval?" required />
            </label>
            <button className="danger" type="submit">Reject draft</button>
          </form>
        </div>
      </article>
    </section>
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

function reviewQueueHref(page: number, draftId?: string) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  if (draftId) params.set("draft", draftId);
  return `/admin/regulatory/review?${params.toString()}`;
}
