import { generateObject } from "ai";
import { openai } from "@ai-sdk/openai";
import type { SourceChunk } from "../types";
import { buildRegulatoryDraftPrompt } from "./draft-prompts";
import { draftRuleCardSchema, type DraftRuleCard } from "./draft-schemas";

export function createDeterministicRuleCardDraft(chunks: SourceChunk[], ruleArea: string): DraftRuleCard {
  return {
    title: `Draft ${ruleArea} rule card`,
    ruleArea,
    decisionQuestion: `Does the customer evidence satisfy the ${ruleArea} obligation?`,
    sourceChunkIds: chunks.map((chunk) => chunk.chunkId),
    extractedConditions: chunks.flatMap((chunk) => extractConditions(chunk.text)),
    deterministicLogic: `evaluate_${ruleArea.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}`,
    allowedFindingStates: chunks.some((chunk) => chunk.isFinalizedSource === false)
      ? ["needs_expert_review", "proposed_change"]
      : ["pass", "gap", "missing_evidence", "not_determined"],
    uncertaintyNotes: ["Draft generated from source chunks and requires FSMA expert review."],
    requiresExpertReview: true
  };
}

export async function draftRuleCard(chunks: SourceChunk[], ruleArea: string): Promise<DraftRuleCard> {
  if (!process.env.OPENAI_API_KEY) return createDeterministicRuleCardDraft(chunks, ruleArea);
  const result = await generateObject({
    model: openai(process.env.OPENAI_MODEL_RULE_DRAFT ?? "gpt-5-mini"),
    schema: draftRuleCardSchema,
    prompt: JSON.stringify(buildRegulatoryDraftPrompt(chunks, "rule_card"))
  });
  return { ...result.object, requiresExpertReview: true };
}

export function validateRuleCardDraft(draft: unknown) {
  return draftRuleCardSchema.safeParse(draft);
}

function extractConditions(text: string) {
  return text
    .split(/[.;]/)
    .map((part) => part.trim())
    .filter((part) => /\b(if|when|unless|where|provided that)\b/i.test(part));
}
