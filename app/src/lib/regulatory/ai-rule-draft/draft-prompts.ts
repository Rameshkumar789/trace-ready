import type { SourceChunk } from "../types";

export function buildRegulatoryDraftPrompt(chunks: SourceChunk[], target: "rule_card" | "kde_requirement") {
  return {
    promptVersion: "regulatory-draft-v1",
    instruction:
      "Draft structured regulatory artifacts only. Include cited source chunk IDs, conditions, applies-when logic, and uncertainty notes. Do not approve or create final compliance conclusions.",
    target,
    chunks: chunks.map((chunk) => ({
      chunkId: chunk.chunkId,
      citation: chunk.citation,
      authorityRank: chunk.authorityRank,
      isFinalizedSource: chunk.isFinalizedSource,
      text: chunk.text,
      summary: chunk.summary
    }))
  };
}
