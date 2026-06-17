import { z } from "zod";

export const aiRuleCardDraftSchema = z.object({
  title: z.string().min(1),
  plainEnglishInterpretation: z.string().min(1),
  appliesTo: z.array(z.string()).default([]),
  doesNotApplyTo: z.array(z.string()).default([]),
  evidenceRequired: z.array(z.string()).default([]),
  customerQuestion: z.string().min(1),
  systemCheck: z.string().min(1),
  possibleOutcomes: z.array(z.string()).min(1),
  severityMapping: z.record(z.string()),
  confidence: z.number().min(0).max(1),
  requiresExpertReview: z.boolean(),
  sourceChunkIds: z.array(z.string()).min(1),
  uncertaintyNotes: z.array(z.string()).default([])
});

export type AiRuleCardDraft = z.infer<typeof aiRuleCardDraftSchema>;
