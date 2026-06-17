import { z } from "zod";

export const aiScenarioDraftSchema = z.object({
  name: z.string().min(1),
  customerRole: z.string().min(1),
  productScope: z.string().min(1),
  requiredCtes: z.array(z.string()).default([]),
  requiredKdes: z.array(z.string()).default([]),
  tlcAssignmentPreservationRule: z.string().min(1),
  operationalFailureMode: z.string().min(1),
  expectedRecords: z.array(z.string()).default([]),
  likelyCustomerEvidence: z.array(z.string()).default([]),
  knownAmbiguity: z.string().default(""),
  expectedFindingOutcome: z.string().min(1),
  interpretationStatus: z.string().min(1),
  expertReviewRequired: z.boolean()
});

export type AiScenarioDraft = z.infer<typeof aiScenarioDraftSchema>;
