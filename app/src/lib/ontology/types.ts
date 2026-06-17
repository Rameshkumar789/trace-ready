export type CoveredEntityStatus =
  | "covered"
  | "not_covered"
  | "exempt"
  | "partially_exempt"
  | "not_determined";

export type ProductScopeStatus = "covered" | "not_covered" | "exempt" | "partially_exempt" | "not_determined";

export type CTEType =
  | "harvest"
  | "cooling"
  | "initial_packing"
  | "first_land_based_receiving"
  | "shipping"
  | "receiving"
  | "transformation";

export type FindingState =
  | "pass"
  | "gap"
  | "conflict"
  | "missing_evidence"
  | "not_applicable"
  | "not_determined"
  | "cannot_determine"
  | "needs_expert_review"
  | "proposed_change"
  | "operational_anomaly";

export type FindingSeverity = "low" | "medium" | "high" | "critical";

export interface BusinessProfile {
  businessId: string;
  companyName: string;
  businessType?: string;
  handlesFtlFoods?: boolean | "unknown";
  coveredEntityStatus: CoveredEntityStatus;
  evidenceRefs: EvidenceRef[];
}

export interface ExemptionClaim {
  claimId: string;
  claimType: string;
  claimedBy: string;
  evidenceProvided: boolean;
  decision: CoveredEntityStatus | "not_determined";
  evidenceRefs: EvidenceRef[];
}

export interface FTLItem {
  productId: string;
  productName: string;
  ftlCategory?: string;
  isFtlMaybe: boolean | "unknown";
}

export interface ProductScopeDecision {
  productId: string;
  status: ProductScopeStatus;
  reason: string;
  evidenceRefs: EvidenceRef[];
}

export interface KDE {
  kdeId: string;
  eventId: string;
  eventLineId?: string;
  cteType: CTEType;
  kdeName: string;
  fieldKey: string;
  value?: string;
  status: "present" | "missing" | "conflicting" | "not_applicable" | "unknown";
  evidenceRefs: EvidenceRef[];
}

export interface KDERequirement {
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

export interface TraceabilityLotCode {
  value: string;
  sourceLocationId?: string;
  sourceReference?: string;
  generatorContact?: string;
}

export interface TraceabilityPlan {
  exists: boolean;
  recordMaintenanceProcedure?: string;
  ftlIdentificationProcedure?: string;
  tlcAssignmentProcedure?: string;
  pointOfContact?: string;
  farmMapAvailable?: boolean | "not_applicable" | "unknown";
  evidenceRefs: EvidenceRef[];
}

export interface TraceabilityEvent {
  eventId: string;
  sourceSystem?: string;
  eventType: CTEType;
  eventDatetime?: string;
  actorLocationId?: string;
  fromPartnerId?: string;
  toPartnerId?: string;
  referenceRecordType?: string;
  referenceRecordNo?: string;
  eventStatus?: string;
}

export interface EventLineItem {
  eventLineId: string;
  eventId: string;
  productId: string;
  productName: string;
  ftlCategory?: string;
  lotOrTlc?: string;
  quantity?: number;
  unit?: string;
  sourceLotOrTlc?: string;
  outputLotOrTlc?: string;
}

export interface TLCLineage {
  lineageId: string;
  relationshipType: string;
  sourceEventId?: string;
  sourceEventLineId?: string;
  sourceLotOrTlc?: string;
  targetEventId?: string;
  targetEventLineId?: string;
  targetLotOrTlc?: string;
  lineageStatus: "linked" | "gap" | "conflicting" | "unverified";
}

export interface SourceDocument {
  evidenceId: string;
  eventId?: string;
  eventLineId?: string;
  evidenceType: string;
  fileOrUrl?: string;
  referenceNo?: string;
  evidenceStatus: "available" | "missing" | "optional" | "unverified";
}

export interface EvidenceRef {
  sheet?: string;
  row?: number;
  field?: string;
  evidenceId?: string;
  sourceValue?: string;
}

export interface NormalizedAuditDataset {
  businessProfiles: BusinessProfile[];
  exemptionClaims: ExemptionClaim[];
  products: FTLItem[];
  productScopeDecisions: ProductScopeDecision[];
  traceabilityPlans: TraceabilityPlan[];
  events: TraceabilityEvent[];
  lineItems: EventLineItem[];
  kdeValues: KDE[];
  lineage: TLCLineage[];
  sourceDocuments: SourceDocument[];
}
