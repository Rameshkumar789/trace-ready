import { AppShell } from "@/components/AppShell";
import { listSourceChunks } from "@/lib/regulatory/regulatory-admin-db";

export default async function SourceChunksPage() {
  const chunks = await listSourceChunks();

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          <h1>Source Chunks</h1>
          <p className="muted">Legal-meaning chunks with citations, source hashes, and authority metadata.</p>
        </div>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Chunk</th>
              <th>Citation</th>
              <th>Authority</th>
              <th>Final</th>
              <th>Hash</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {chunks.map((chunk) => (
                <tr key={chunk.id}>
                  <td>{chunk.section_label}</td>
                  <td>{chunk.citation}</td>
                  <td>{chunk.authority_rank ?? "unknown"}</td>
                  <td>{chunk.status}</td>
                  <td>{chunk.text_hash}</td>
                  <td>{chunk.summary}</td>
                </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
