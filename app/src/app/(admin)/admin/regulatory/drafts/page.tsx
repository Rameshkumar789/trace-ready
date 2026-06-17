import { AppShell } from "@/components/AppShell";
import { arrayLength, listDraftRecords } from "@/lib/regulatory/regulatory-admin-db";

export default async function RegulatoryDraftsPage() {
  const drafts = await listDraftRecords(1000);
  const visibleDrafts = drafts.slice(0, 250);
  const readyForReview = drafts.filter((draft) => draft.review_status === "needs_review" && draft.schema_valid && draft.citation_valid).length;
  const approved = drafts.filter((draft) => draft.review_status === "approved").length;
  const rejected = drafts.filter((draft) => draft.review_status === "rejected").length;
  const blocked = drafts.filter((draft) => draft.review_status === "needs_review" && (!draft.schema_valid || !draft.citation_valid)).length;

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Rule Card Drafts</h1>
          <p className="muted">Draft regulatory artifacts waiting for consultant/legal review. Drafts do not become executable until approved and published into an approved package.</p>
        </div>
      </div>
      <section className="reviewer-triage" aria-label="Rule card draft summary">
        <DraftMetric label="Total Drafts" value={drafts.length} detail={`${visibleDrafts.length} shown`} />
        <DraftMetric label="Ready For Review" value={readyForReview} detail="schema-valid and citation-valid" />
        <DraftMetric label="Blocked Drafts" value={blocked} detail="needs correction before approval" />
        <DraftMetric label="Approved / Rejected" value={`${approved}/${rejected}`} detail="review decisions recorded" />
      </section>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Draft</th>
              <th>Collection</th>
              <th>Phase</th>
              <th>Chunks</th>
              <th>Schema</th>
              <th>Citations</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visibleDrafts.map((draft) => (
              <tr id={draft.id} key={draft.id}>
                <td>{draft.record_id}</td>
                <td>{draft.collection}</td>
                <td>{draft.source_phase}</td>
                <td>{arrayLength(draft.source_chunk_ids)}</td>
                <td><span className={`badge ${draft.schema_valid ? "ok" : "danger"}`}>{draft.schema_valid ? "valid" : "invalid"}</span></td>
                <td><span className={`badge ${draft.citation_valid ? "ok" : "danger"}`}>{draft.citation_coverage_status}</span></td>
                <td><span className={draft.review_status === "rejected" ? "badge danger" : "badge warn"}>{draft.review_status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}

function DraftMetric({ label, value, detail }: { label: string; value: number | string; detail: string }) {
  return (
    <div className="reviewer-triage-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
