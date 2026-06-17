import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { listRegulatorySources, type RegulatorySourceRow } from "@/lib/regulatory/regulatory-admin-db";

const AUTHORITY_ORDER = ["codified_rule", "final_rule", "guidance", "template", "scenario", "support"];

export default async function RegulatorySourcesPage() {
  const sources = await listRegulatorySources(500);
  const selectedSource = selectPrimarySource(sources);
  const totalChunks = sources.reduce((sum, source) => sum + (source.chunkCount ?? 0), 0);
  const officialSources = sources.filter((source) => ["codified_rule", "final_rule"].includes(source.authority_rank)).length;
  const finalizedSources = sources.filter((source) => source.is_finalized).length;
  const sourceTypes = new Set(sources.map((source) => source.source_type)).size;
  const statusCounts = countBy(sources, (source) => source.source_status || "unknown");
  const authorityCounts = countBy(sources, (source) => source.authority_rank || "unknown");

  return (
    <AppShell>
      <div className="source-library-page">
        <header className="source-library-header">
          <div>
            <span className="eyebrow">Advanced Regulatory Admin</span>
            <h1>Source Library</h1>
            <p>
              Official FDA, eCFR, Federal Register, guidance, template, and scenario sources used to create source chunks and reviewer-approved rule packages.
            </p>
          </div>
          <div className="source-header-actions">
            <Link className="button secondary" href="/admin/regulatory/chunks">Open Chunks</Link>
            <Link className="button" href="/admin/regulatory/review">Review Cards</Link>
          </div>
        </header>

        <section className="source-kpi-strip" aria-label="Source library summary">
          <SourceMetric label="Sources" value={sources.length} detail={`${officialSources} binding/legal-history sources`} />
          <SourceMetric label="Chunks" value={totalChunks} detail="citation-addressable records" />
          <SourceMetric label="Finalized" value={finalizedSources} detail="available for approved packages" />
          <SourceMetric label="Types" value={sourceTypes} detail="documents, pages, templates, scenarios" />
        </section>

        <section className="source-workbench" aria-label="Source library workbench">
          <div className="source-table-panel">
            <div className="source-toolbar">
              <div>
                <h2>Registry</h2>
                <p className="muted">Review source authority, chunk coverage, version metadata, and traceability before approving drafted cards.</p>
              </div>
              <div className="source-search-shell" aria-hidden="true">
                <span>Search source, citation, URL</span>
                <kbd>/</kbd>
              </div>
            </div>

            <div className="source-filter-row" aria-label="Authority filters">
              {AUTHORITY_ORDER.map((authority) => (
                <span className="source-filter-chip" key={authority}>
                  {formatLabel(authority)}
                  <strong>{authorityCounts[authority] ?? 0}</strong>
                </span>
              ))}
            </div>

            <div className="source-table">
              <div className="source-table-head">
                <span>Source</span>
                <span>Authority</span>
                <span>Status</span>
                <span>Chunks</span>
                <span>Retrieved</span>
                <span>Integrity</span>
              </div>
              {sources.map((source) => (
                <Link className="source-table-row" href={`/admin/regulatory/sources/${source.id}`} key={source.id}>
                  <span className="source-title-cell">
                    <strong>{source.title}</strong>
                    <small>{source.citation || source.id}</small>
                  </span>
                  <span><StatusPill value={source.authority_rank} tone={authorityTone(source.authority_rank)} /></span>
                  <span><StatusPill value={source.source_status} tone={source.source_status === "active" ? "ok" : "warn"} /></span>
                  <span className="source-number">{source.chunkCount ?? 0}</span>
                  <span className="source-date">{formatDate(source.retrieved_at)}</span>
                  <span><StatusPill value={integrityLabel(source)} tone={source.text_hash ? "ok" : "danger"} /></span>
                </Link>
              ))}
            </div>
          </div>

          <aside className="source-inspector" aria-label="Selected source inspector">
            <div className="source-inspector-header">
              <span className="eyebrow">Selected Source</span>
              <h2>{selectedSource?.title ?? "No source selected"}</h2>
              {selectedSource ? <p>{selectedSource.summary || selectedSource.citation || selectedSource.id}</p> : null}
            </div>

            {selectedSource ? (
              <>
                <div className="source-inspector-grid">
                  <InspectorItem label="Authority" value={formatLabel(selectedSource.authority_rank)} />
                  <InspectorItem label="Status" value={formatLabel(selectedSource.source_status)} />
                  <InspectorItem label="Chunks" value={String(selectedSource.chunkCount ?? 0)} />
                  <InspectorItem label="Final Source" value={selectedSource.is_finalized ? "Yes" : "No"} />
                </div>

                <div className="source-trust-list">
                  <TrustRow label="Source hash" value={shortHash(selectedSource.text_hash)} state={selectedSource.text_hash ? "ok" : "risk"} />
                  <TrustRow label="Citation anchor" value={selectedSource.citation || "Not set"} state={selectedSource.citation ? "ok" : "risk"} />
                  <TrustRow label="Retrieved" value={formatDate(selectedSource.retrieved_at)} state="ok" />
                  <TrustRow label="Effective" value={formatDate(selectedSource.effective_date)} state={selectedSource.effective_date ? "ok" : "neutral"} />
                  <TrustRow label="Compliance" value={formatDate(selectedSource.compliance_date)} state={selectedSource.compliance_date ? "ok" : "neutral"} />
                </div>

                <div className="source-url-box">
                  <span>Official URL</span>
                  <a href={selectedSource.url} rel="noreferrer" target="_blank">{selectedSource.url}</a>
                </div>

                <div className="source-status-stack">
                  {Object.entries(statusCounts).map(([status, count]) => (
                    <div key={status}>
                      <span>{formatLabel(status)}</span>
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="muted">No regulatory source rows were returned from the database.</p>
            )}
          </aside>
        </section>
      </div>
    </AppShell>
  );
}

function SourceMetric({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <small>{detail}</small>
    </div>
  );
}

function InspectorItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TrustRow({ label, value, state }: { label: string; value: string; state: "ok" | "risk" | "neutral" }) {
  return (
    <div className={`source-trust-row ${state}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusPill({ value, tone }: { value: string; tone: "ok" | "warn" | "danger" | "neutral" }) {
  return <span className={`source-status-pill ${tone}`}>{formatLabel(value || "unknown")}</span>;
}

function selectPrimarySource(sources: RegulatorySourceRow[]) {
  return sources.find((source) => source.authority_rank === "codified_rule") ?? sources.find((source) => source.is_finalized) ?? sources[0];
}

function countBy<T>(items: T[], selector: (item: T) => string) {
  return items.reduce<Record<string, number>>((counts, item) => {
    const key = selector(item);
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
}

function authorityTone(authority: string): "ok" | "warn" | "danger" | "neutral" {
  if (authority === "codified_rule" || authority === "final_rule") return "ok";
  if (authority === "guidance" || authority === "template") return "warn";
  if (!authority) return "danger";
  return "neutral";
}

function integrityLabel(source: RegulatorySourceRow) {
  if (!source.text_hash) return "Hash missing";
  if (!source.chunkCount) return "No chunks";
  return "Verified";
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string | null) {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function shortHash(value: string | null) {
  if (!value) return "Missing";
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}
