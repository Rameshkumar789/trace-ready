import type { RuleCard, SourceChunk } from "@/lib/regulatory/types";

export function buildDraftScenarioPrompt(ruleCard: RuleCard, chunks: SourceChunk[], scenarioGroup: string) {
  return {
    promptVersion: "draft-scenario-case-v1",
    instruction:
      "Draft a scenario fixture for human approval. Expected outcomes must be reviewed before becoming regression tests.",
    scenarioGroup,
    ruleCard,
    sourceChunks: chunks.map((chunk) => ({
      chunkId: chunk.chunkId,
      citation: chunk.citation,
      summary: chunk.summary
    }))
  };
}
