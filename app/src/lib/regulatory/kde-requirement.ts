import { z } from "zod";

export const kdeRequirementSchema = z.object({
  kdeRequirementId: z.string().min(1),
  cteType: z.enum([
    "harvest",
    "cooling",
    "initial_packing",
    "first_land_based_receiving",
    "shipping",
    "receiving",
    "transformation"
  ]),
  kdeName: z.string().min(1),
  fieldKey: z.string().min(1),
  requiredStatus: z.enum(["required", "conditional", "not_applicable"]),
  appliesWhen: z.string().min(1),
  sourceChunkId: z.string().min(1),
  ruleCardId: z.string().min(1),
  exampleValue: z.string().optional(),
  severityIfMissing: z.enum(["low", "medium", "high", "critical"]),
  status: z.enum(["draft", "in_review", "approved", "deprecated"]),
  reviewedBy: z.string().optional(),
  reviewedAt: z.string().optional(),
  version: z.number().int().positive()
});
