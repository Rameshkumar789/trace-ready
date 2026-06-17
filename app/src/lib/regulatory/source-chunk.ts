import type { SourceChunk } from "./types";

export function getActiveChunks(chunks: SourceChunk[]) {
  return chunks.filter((chunk) => chunk.status === "active");
}

export function findChunksByIds(chunks: SourceChunk[], chunkIds: string[]) {
  const byId = new Map(chunks.map((chunk) => [chunk.chunkId, chunk]));
  return chunkIds.map((id) => byId.get(id)).filter((chunk): chunk is SourceChunk => Boolean(chunk));
}

export function chunkHasAuditCitation(chunk: SourceChunk) {
  return chunk.status === "active" && chunk.citation.length > 0 && chunk.textHash.startsWith("sha256:");
}
