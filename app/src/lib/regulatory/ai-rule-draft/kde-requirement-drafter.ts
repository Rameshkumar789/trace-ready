import { generateObject } from "ai";
import { openai } from "@ai-sdk/openai";
import type { SourceChunk } from "../types";
import { buildRegulatoryDraftPrompt } from "./draft-prompts";
import { draftKdeRequirementSchema, type DraftKdeRequirement } from "./draft-schemas";

export function createDeterministicKdeDraft(chunk: SourceChunk, cteType: string, kdeName: string): DraftKdeRequirement {
  return {
    cteType,
    kdeName,
    fieldKey: kdeName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""),
    requiredStatus: chunk.text.toLowerCase().includes("when") ? "conditional" : "required",
    appliesWhen: `Applies when ${cteType} records are present and the cited source chunk is finalized or review-ready.`,
    sourceChunkId: chunk.chunkId,
    severityIfMissing: "high",
    uncertaintyNotes: ["Draft KDE requirement requires FSMA expert review before publication."],
    requiresExpertReview: true
  };
}

export async function draftKdeRequirement(chunk: SourceChunk, cteType: string, kdeName: string): Promise<DraftKdeRequirement> {
  if (!process.env.OPENAI_API_KEY) return createDeterministicKdeDraft(chunk, cteType, kdeName);
  const result = await generateObject({
    model: openai(process.env.OPENAI_MODEL_RULE_DRAFT ?? "gpt-5-mini"),
    schema: draftKdeRequirementSchema,
    prompt: JSON.stringify({
      ...buildRegulatoryDraftPrompt([chunk], "kde_requirement"),
      cteType,
      kdeName
    })
  });
  return { ...result.object, requiresExpertReview: true };
}

export function validateKdeDraft(draft: unknown) {
  return draftKdeRequirementSchema.safeParse(draft);
}
