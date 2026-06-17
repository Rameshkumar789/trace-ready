import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { loadRegulatorySourceDetail } from "@/lib/regulatory/regulatory-admin-db";

export default async function RegulatorySourceDetailPage({ params }: { params: Promise<{ sourceId: string }> }) {
  const { sourceId } = await params;
  const detail = await loadRegulatorySourceDetail(sourceId);
  if (!detail) notFound();
  const { source, chunks: sourceChunks } = detail;

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>{source.title}</h1>
          <p className="muted">{source.citation}</p>
        </div>
        <span className={`badge ${source.is_finalized ? "ok" : "warn"}`}>{source.source_status}</span>
      </div>
      <section className="grid two">
        <div className="panel">
          <h2>Source Metadata</h2>
          <table>
            <tbody>
              <tr><td>Authority rank</td><td>{source.authority_rank}</td></tr>
              <tr><td>Published</td><td>{source.published_date ?? "not listed"}</td></tr>
              <tr><td>Effective</td><td>{source.effective_date ?? "not listed"}</td></tr>
              <tr><td>Compliance</td><td>{source.compliance_date ?? "not listed"}</td></tr>
              <tr><td>Retrieved</td><td>{source.retrieved_at}</td></tr>
              <tr><td>Hash</td><td>{source.text_hash}</td></tr>
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h2>Chunks</h2>
          <ul>
            {sourceChunks.map((chunk) => (
              <li key={chunk.id}>{chunk.citation}: {chunk.section_label}</li>
            ))}
          </ul>
        </div>
      </section>
    </AppShell>
  );
}
