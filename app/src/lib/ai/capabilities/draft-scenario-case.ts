import { aiScenarioDraftSchema, type AiScenarioDraft } from "@/lib/schemas/ai-scenario-draft";
import type { RuleCard, SourceChunk } from "@/lib/regulatory/types";
import { buildDraftScenarioPrompt } from "@/lib/ai/prompts/draft-scenario-case";
import { generateObject } from "ai";
import { openai } from "@ai-sdk/openai";

export function validateAiScenarioDraft(output: unknown) {
  return aiScenarioDraftSchema.safeParse(output);
}

export function createManualScenarioDraft(ruleCard: RuleCard, chunks: SourceChunk[], scenarioGroup: string): AiScenarioDraft {
  buildDraftScenarioPrompt(ruleCard, chunks, scenarioGroup);
  return {
    name: `Draft ${scenarioGroup} scenario`,
    customerRole: "operator",
    productScope: "not_determined",
    requiredCtes: ruleCard.cteType ? [ruleCard.cteType] : [],
    requiredKdes: [],
    tlcAssignmentPreservationRule: "Needs human approval.",
    operationalFailureMode: "Missing or conflicting evidence.",
    expectedRecords: chunks.map((chunk) => chunk.citation),
    likelyCustomerEvidence: ["workbook row", "source document"],
    knownAmbiguity: "Draft scenario; expected outcome not approved.",
    expectedFindingOutcome: "needs_expert_review",
    interpretationStatus: "needs_expert_review",
    expertReviewRequired: true
  };
}

export async function draftScenarioWithAi(ruleCard: RuleCard, chunks: SourceChunk[], scenarioGroup: string): Promise<AiScenarioDraft> {
  if (!process.env.OPENAI_API_KEY) {
    return createManualScenarioDraft(ruleCard, chunks, scenarioGroup);
  }
  const prompt = buildDraftScenarioPrompt(ruleCard, chunks, scenarioGroup);
  const result = await generateObject({
    model: openai(process.env.OPENAI_MODEL_RULE_DRAFT ?? "gpt-5-mini"),
    schema: aiScenarioDraftSchema,
    prompt: JSON.stringify(prompt)
  });
  return {
    ...result.object,
    expertReviewRequired: true,
    interpretationStatus: result.object.interpretationStatus || "needs_expert_review"
  };
}
