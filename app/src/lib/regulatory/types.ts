import type { CTEType, FindingSeverity, FindingState } from "@/lib/ontology/types";

export type SourceStatus =
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

export interface CitationAnchor {
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

export interface SourceLibraryRecord {
  source: RegulatorySource;
  versions: SourceVersionRecord[];
  artifacts: SourceArtifactRecord[];
  chunks: SourceChunk[];
}

export interface SourceVersionRecord {
  sourceVersionId: string;
  sourceId: string;
  version: number;
  rawTextHash: string;
  normalizedTextHash: string;
  createdAt: string;
  supersedesVersion?: number;
}

export interface SourceArtifactRecord {
  artifactId: string;
  sourceId: string;
  sourceVersionId: string;
  artifactType: "raw_snapshot" | "normalized_text" | "table_json";
  storageKey: string;
  hash: string;
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

export interface RegulatoryDraft<TDraft> {
  draftId: string;
  draftType: "rule_card" | "kde_requirement";
  sourceChunkIds: string[];
  draft: TDraft;
  validationErrors: string[];
  status: "draft" | "rejected" | "ready_for_review" | "approved";
  createdBy: "ai" | "human";
  createdAt: string;
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

export type IntelligenceReviewStatus = "draft" | "needs_review" | "approved" | "rejected" | "superseded" | "conflict_detected";

export interface IntelligenceDraftReviewRecord {
  draft_id: string;
  collection: string;
  record_id: string;
  source_phase: string;
  extraction_method: string;
  confidence: string;
  review_status: IntelligenceReviewStatus;
  source_chunk_ids: string[];
  citation_count: number;
  citation_coverage_status: string;
  schema_valid: boolean;
  citation_valid: boolean;
  validation_errors: string[];
  reviewer_blockers: string[];
  payload: Record<string, unknown>;
}

export interface IntelligenceReviewActionLogEntry {
  action_id: string;
  target_id: string;
  action: string;
  actor: string;
  actor_role: string;
  reason: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

export interface Phase6ReviewPackage {
  summary: {
    generatedAt: string;
    draftRecords: number;
    readyForReview: number;
    rejectedRecords: number;
    approvedRecords: number;
    reviewActions: number;
    statusCounts: Record<string, number>;
    collectionCounts: Record<string, number>;
    sourcePhaseCounts: Record<string, number>;
    citationCoverage: Record<string, number>;
    approvedRecordsPolicy: string;
  };
  draft_records: IntelligenceDraftReviewRecord[];
  rejected_records: IntelligenceDraftReviewRecord[];
  approved_records: Record<string, unknown>[];
  review_action_log: IntelligenceReviewActionLogEntry[];
  citation_coverage_report: Record<string, unknown>;
}
