import { z } from "zod";

export const draftRuleCardSchema = z.object({
  title: z.string().min(1),
  ruleArea: z.string().min(1),
  decisionQuestion: z.string().min(1),
  sourceChunkIds: z.array(z.string().min(1)).min(1),
  extractedConditions: z.array(z.string()).default([]),
  deterministicLogic: z.string().min(1),
  allowedFindingStates: z.array(z.string().min(1)).min(1),
  uncertaintyNotes: z.array(z.string()).default([]),
  requiresExpertReview: z.literal(true)
});

export const draftKdeRequirementSchema = z.object({
  cteType: z.string().min(1),
  kdeName: z.string().min(1),
  fieldKey: z.string().min(1),
  requiredStatus: z.enum(["required", "conditional", "not_applicable"]),
  appliesWhen: z.string().min(1),
  sourceChunkId: z.string().min(1),
  severityIfMissing: z.enum(["low", "medium", "high", "critical"]),
  uncertaintyNotes: z.array(z.string()).default([]),
  requiresExpertReview: z.literal(true)
});

export type DraftRuleCard = z.infer<typeof draftRuleCardSchema>;
export type DraftKdeRequirement = z.infer<typeof draftKdeRequirementSchema>;
