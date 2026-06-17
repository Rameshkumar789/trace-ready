import { z } from "zod";

export const ruleCardSchema = z.object({
  ruleCardId: z.string().min(1),
  ruleArea: z.string().min(1),
  cteType: z.string().nullable(),
  decisionQuestion: z.string().min(1),
  sourceChunkIds: z.array(z.string().min(1)).min(1),
  authorityRank: z.number().int().positive(),
  isFinalizedSource: z.boolean(),
  effectiveDate: z.string().nullable(),
  complianceDate: z.string().nullable(),
  conditions: z.array(z.string()).default([]),
  deterministicLogic: z.string().min(1),
  allowedFindingStates: z.array(z.string().min(1)).min(1),
  status: z.enum(["draft", "in_review", "approved", "deprecated"]),
  reviewedBy: z.string().optional(),
  reviewedAt: z.string().optional(),
  version: z.number().int().positive()
});

export type RuleCardInput = z.infer<typeof ruleCardSchema>;
