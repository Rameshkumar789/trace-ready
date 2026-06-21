import type { CTEType, FindingSeverity, FindingState } from "@/lib/ontology/types";

type SourceStatus =
  | "codified_rule"
  | "final_rule"
  | "technical_amendment"
  | "proposed_rule"
  | "draft_guidance"
  | "guidance"
  | "faq"
  | "discussion_paper"
  | "public_meeting"
  | "internal_interpretation"
  | "ingested";

export interface RegulatorySource {
  sourceId: string;
  title: string;
  sourceType: string;
  sourceStatus: SourceStatus;
  authorityRank: number | string;
  url: string;
  citation: string;
  publishedDate: string | null;
  effectiveDate: string | null;
  complianceDate: string | null;
  isFinalized: boolean;
  retrievedAt: string;
  textHash: string;
  supersedes: string[];
  supersededBy: string[];
  notes: string;
}

export interface SourceChunk {
  chunkId: string;
  regulatorySourceId: string;
  chunkCode: string;
  sectionLabel: string;
  sourceLocation: string;
  text: string;
  summary: string;
  citation: string;
  textHash: string;
  status: "active" | "deprecated" | "superseded";
  authorityRank?: number | string;
  isFinalizedSource?: boolean;
  retrievedAt?: string;
  sourceUrl?: string;
  version?: number;
  anchors?: CitationAnchor[];
}

interface CitationAnchor {
  sourceId: string;
  citation: string;
  section?: string;
  paragraph?: string;
  tableLabel?: string;
  pageNumber?: number;
  url?: string;
  retrievedAt?: string;
  sourceHash?: string;
}

export interface RuleCard {
  ruleCardId: string;
  ruleArea: string;
  cteType: CTEType | "harvest_cooling" | null;
  decisionQuestion: string;
  sourceChunkIds: string[];
  authorityRank: number;
  isFinalizedSource: boolean;
  effectiveDate: string | null;
  complianceDate: string | null;
  conditions: string[];
  deterministicLogic: string;
  allowedFindingStates: FindingState[];
  status: "draft" | "in_review" | "approved" | "deprecated";
  reviewedBy?: string;
  reviewedAt?: string;
  version: number;
}

export interface KdeRequirementRecord {
  kdeRequirementId: string;
  cteType: CTEType;
  kdeName: string;
  fieldKey: string;
  requiredStatus: "required" | "conditional" | "not_applicable";
  appliesWhen: string;
  sourceChunkId: string;
  ruleCardId: string;
  exampleValue?: string;
  severityIfMissing: FindingSeverity;
  status: "draft" | "in_review" | "approved" | "deprecated";
  reviewedBy?: string;
  reviewedAt?: string;
  version: number;
}

export interface ScenarioCase {
  scenarioId: string;
  name: string;
  scenarioGroup: string;
  sourceCitations: string[];
  linkedRuleCardIds: string[];
  evidenceFixture: Record<string, unknown>;
  expectedFindings: string[];
  expectedStatus: FindingState;
  requiresExpertReview: boolean;
  status: "draft" | "approved" | "deprecated";
}

export interface RegulatoryObligation {
  obligationId: string;
  obligationText: string;
  obligationArea: string;
  cteType?: CTEType | "harvest_cooling";
  sourceChunkIds: string[];
  ruleCardIds: string[];
  kdeRequirementIds: string[];
  deterministicCheckIds: string[];
  status: "draft" | "approved" | "deprecated";
  reviewedBy?: string;
  reviewedAt?: string;
  version: number;
}

