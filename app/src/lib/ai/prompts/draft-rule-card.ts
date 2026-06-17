import type { SourceChunk } from "@/lib/regulatory/types";

export function buildDraftRuleCardPrompt(chunks: SourceChunk[], targetRuleGroup: string) {
  return {
    promptVersion: "draft-rule-card-v1",
    instruction:
      "Draft a structured rule card from the supplied source chunks. Do not approve it. Do not make final compliance conclusions.",
    targetRuleGroup,
    sourceChunks: chunks.map((chunk) => ({
      chunkId: chunk.chunkId,
      citation: chunk.citation,
      text: chunk.text,
      summary: chunk.summary
    }))
  };
}
