import { aiRuleCardDraftSchema, type AiRuleCardDraft } from "@/lib/schemas/ai-rule-card-draft";
import type { SourceChunk } from "@/lib/regulatory/types";
import { buildDraftRuleCardPrompt } from "@/lib/ai/prompts/draft-rule-card";
import { generateObject } from "ai";
import { openai } from "@ai-sdk/openai";

export function validateAiRuleCardDraft(output: unknown) {
  return aiRuleCardDraftSchema.safeParse(output);
}

export function createManualRuleCardDraft(chunks: SourceChunk[], targetRuleGroup: string): AiRuleCardDraft {
  const prompt = buildDraftRuleCardPrompt(chunks, targetRuleGroup);
  return {
    title: `Draft ${targetRuleGroup} rule card`,
    plainEnglishInterpretation: "Draft-only interpretation pending human regulatory review.",
    appliesTo: [targetRuleGroup],
    doesNotApplyTo: [],
    evidenceRequired: chunks.map((chunk) => chunk.citation),
    customerQuestion: `Does ${targetRuleGroup} apply to the supplied evidence?`,
    systemCheck: "Draft-only; cannot execute until approved.",
    possibleOutcomes: ["draft", "needs_expert_review"],
    severityMapping: { draft: "medium" },
    confidence: 0.5,
    requiresExpertReview: true,
    sourceChunkIds: prompt.sourceChunks.map((chunk) => chunk.chunkId),
    uncertaintyNotes: ["Generated as a draft placeholder; not customer-facing."]
  };
}

export async function draftRuleCardWithAi(chunks: SourceChunk[], targetRuleGroup: string): Promise<AiRuleCardDraft> {
  if (!process.env.OPENAI_API_KEY) {
    return createManualRuleCardDraft(chunks, targetRuleGroup);
  }
  const prompt = buildDraftRuleCardPrompt(chunks, targetRuleGroup);
  const result = await generateObject({
    model: openai(process.env.OPENAI_MODEL_RULE_DRAFT ?? "gpt-5-mini"),
    schema: aiRuleCardDraftSchema,
    prompt: JSON.stringify(prompt)
  });
  return {
    ...result.object,
    requiresExpertReview: true
  };
}
